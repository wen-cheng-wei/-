RunScript_41b4f65e_679c_4705_b74a_96e8191c2444 = {}

local label = {'码','标'}
--自定义roi矩形区域
local roi = {}

--以下所有向量格式{x:__,y:__}
-- 配置参数
local SCREW_CONFIG = {
    ANGLE_THRESHOLD = 10,       -- 对准角度阈值(°)
    MAX_DISTANCE = 100,         -- 最大有效距离(像素),指螺丝孔到螺丝枪尖端距离，超过该距离则判定失败，需实际现场情况定
    ANGLE_DIFF_THRESHOLD = 5,  -- 角度相近阈值(°)
    WINDOW_SIZE = 10,          -- 滑动窗口大小（要求帧数+5）
    HIT_THRESHOLD = 6,        -- 窗口内最小命中次数（等于你需要检测到的帧数）
    ALARM_TIME_LIMIT = 30,     -- 触发报警时间(s)
    CURRENT_HOLE = 4,       --当前检测的螺丝孔点位 
    ROI_SIZE = 100           --自定义roi矩形区域大小(像素)
}

--工具参数
local TOOL_NAMES = {
    deep_learning_detector = 'DLObjDetect4',    --对象工具名称
    alarm_off_1 = 'AlarmControl1',              --关闭报警工具1
    alarm_off_2 = 'AlarmControl2',              --关闭报警工具2
    alarm_on_1 = 'AlarmControl3',               --开启报警工具1
    alarm_on_2 = 'AlarmControl4',               --开启报警工具2
    mark_point = 'MarkPoint1',                    --标记点工具
}

--滑动窗口
local alignment_window = {}
--螺丝枪的两个点：起始点（螺丝枪中间段的某一个点）和靠近螺丝枪尖端的点，从斑点或模板匹配来
local gun_base_point = {x=-100,y=-100}
local gun_tip_point = {x=-100,y=-100}
--螺丝孔的所有坐标
local holes = {}
--临时，判定正在打的螺丝位置
local hit_aaaa=-100

--时间设定
local start_time=os.time()

--初始化函数（初始化滑动窗口）
function RunScript_41b4f65e_679c_4705_b74a_96e8191c2444.setup(this, ctx)
    alignment_window = {}
end

--执行函数
function RunScript_41b4f65e_679c_4705_b74a_96e8191c2444.exec(this, ctx)
    holes={}
    --报警功能
    local end_time=os.time()
    local speend_time=end_time-start_time
    if speend_time>SCREW_CONFIG.ALARM_TIME_LIMIT then
        local tool1 =ctx:get_tool_by_name(TOOL_NAMES.alarm_on_1)
        local tool2 =ctx:get_tool_by_name(TOOL_NAMES.alarm_on_2)
        tool1:exec(ctx)
        tool2:exec(ctx)
    end

    --获取标记点
    local mark_point_tool =ctx:get_tool_by_name(TOOL_NAMES.mark_point)
    if mark_point_tool == nil then
        LOG.warn('Cannot find ' .. TOOL_NAMES.mark_point)
        return 1, 'Cannot find ' .. TOOL_NAMES.mark_point
    end
    local mark_point_result=mark_point_tool:origin_point_list()
    for _,point in ipairs(mark_point_result) do
        table.insert(holes,point)
    end

    --此处加如果工具识别不到电批，滑动窗口需要添加false且直接返回3，进行下一轮
    local detected_tool =ctx:get_tool_by_name(TOOL_NAMES.deep_learning_detector)
    if  not detected_tool then
        LOG.warn('Cannot find'..TOOL_NAMES.deep_learning_detector)
        return 1,'Cannot find'..TOOL_NAMES.deep_learning_detector
    end

    local gun_base_point_result=false
    local gun_tip_point_result=false

    local detected_result=detected_tool:result()
    for _,obj in ipairs(detected_result) do
        if obj.class_name == label[1] then
            gun_base_point.x,gun_base_point.y = Get_center_Point(obj.bounding)
            gun_base_point_result=true
        end
        if obj.class_name == label[2] then
            gun_tip_point.x,gun_tip_point.y = Get_center_Point(obj.bounding)
            gun_tip_point_result=true
        end
    end

    if gun_base_point_result and gun_tip_point_result then
        local detect_result = Screw_Alignment_Detect(gun_base_point, gun_tip_point, holes, SCREW_CONFIG.CURRENT_HOLE)
        local is_confirmed, err = Check_Continuous_Alignment(detect_result, SCREW_CONFIG.CURRENT_HOLE)
        holes={}
        if is_confirmed then
            LOG.debug('success:'..hit_aaaa)
            return 0 , 'Success'
        elseif err then
            LOG.error('ERROR:'..hit_aaaa)
            local tool1 =ctx:get_tool_by_name(TOOL_NAMES.alarm_on_1)
            local tool2 =ctx:get_tool_by_name(TOOL_NAMES.alarm_on_2)
            tool1:exec(ctx)
            tool2:exec(ctx)
            return 3 , 'errror'
        else
            LOG.info('Not enough quantity')
            return 2 , 'Not enough quantity'
        end
    else
        table.insert(alignment_window,-1)
        LOG.info('Can\' find dianpi')
        return 4 , 'Can\' find dianpi'
    end

end

--清理函数
function RunScript_41b4f65e_679c_4705_b74a_96e8191c2444.cleanup(this, ctx)
    alignment_window = {}
end

--进程开始前准备函数
function RunScript_41b4f65e_679c_4705_b74a_96e8191c2444.on_process_begin(this, ctx)
	alignment_window = {}
    holes = {}
    --关闭报警灯(初始化)
    local tool1 =ctx:get_tool_by_name(TOOL_NAMES.alarm_off_1)
    local tool2 =ctx:get_tool_by_name(TOOL_NAMES.alarm_off_2)
    tool1:exec(ctx)
    tool2:exec(ctx)
    start_time=os.time()
end

function RunScript_41b4f65e_679c_4705_b74a_96e8191c2444.on_process_end(this, ctx)
	alignment_window = {}
    holes = {}
    start_time=os.time()
end


-- 带方向的向量角度计算（-180~180°）,起始向量v1,终点向量v2
local function get_signed_angle(v1, v2)
    local dx1, dy1 = v1.x, v1.y
    local dx2, dy2 = v2.x, v2.y
    
    local dot = dx1*dx2 + dy1*dy2
    local cross = dx1*dy2 - dy1*dx2  -- 叉乘判断方向
    
    local mod1 = math.sqrt(dx1*dx1 + dy1*dy1)
    local mod2 = math.sqrt(dx2*dx2 + dy2*dy2)
    
    if mod1 == 0 or mod2 == 0 then
        return 0.0
    end
    
    local cos_theta = dot / (mod1 * mod2)
    if cos_theta > 1 then cos_theta = 1 end
    if cos_theta < -1 then cos_theta = -1 end
    
    local angle = math.deg(math.acos(cos_theta))
    
    -- 叉乘为负 → 顺时针 → 角度取负
    -- 叉乘为正 → 逆时针 → 角度取正
    if cross < 0 then
        angle = -angle
    end
    
    return angle
end

-- 计算两点距离
local function distance(p1, p2)
    return math.sqrt((p2.x-p1.x)^2 + (p2.y-p1.y)^2)
end

-- 输入：gun_p0(枪身起始点), gun_p1(枪尖端点), screw_holes(螺丝孔列表), current_hole(当前流程应打螺丝孔)
-- 输出：{is_hit=是否命中, hit_hole=命中的螺丝孔, angle=角度差, distance=距离}
-- 该函数可以找出螺丝枪目前对准的孔位，返回是否找到、孔位索引、孔位和螺丝枪的角度、枪身到孔位的距离
function Screw_Alignment_Detect(gun_p0, gun_p1, screw_holes, current_hole)
    -- 防呆（防止误识别的参数传入）
    local gun_len = distance(gun_p0, gun_p1)
    -- if gun_len < 1500 then
    --     return {is_hit=false, hit_hole=nil,angle=nil,distance=nil}
    -- end
    
    -- 构建螺丝枪方向
    local gun_vec = {
        x = gun_p1.x - gun_p0.x,
        y = gun_p1.y - gun_p0.y
    }
    
    -- 遍历所有螺丝孔
    local candidates = {}
    for i, hole in ipairs(screw_holes) do
        -- 孔方向向量（从枪身起始点P0出发）
        local hole_vec = {
            x = hole.x - gun_p0.x,
            y = hole.y - gun_p0.y
        }
        
        -- 计算带方向角度差
        local angle_diff = get_signed_angle(gun_vec, hole_vec)
        local abs_angle = math.abs(angle_diff)
        
        -- 计算起始点P0、螺丝枪尖端p1分别与螺丝孔的距离
        local dist_p0_hole = distance(gun_p0, hole)
        local dist_p1_hole = distance(gun_p1, hole)
        
        -- 是否进入候选标志位
        local is_candidate = true
        
        -- 角度阈值
        local threshold = SCREW_CONFIG.ANGLE_THRESHOLD

        --以下为当前流程孔条件放宽，按实际场景使用
        if current_hole and i == current_hole then
            threshold = threshold + 3
        end

        if abs_angle >= threshold then
            is_candidate = false
        end
        
        -- 最大距离限制（用P1的距离）
        if dist_p1_hole >= SCREW_CONFIG.MAX_DISTANCE then
            is_candidate = false
        end
        
        -- 枪尖必须比枪身更靠近孔（排除背向情况）
        if dist_p1_hole >= dist_p0_hole then
            is_candidate = false
        end
        
        if is_candidate then
            table.insert(candidates, {
                index = i,
                hole = hole,
                angle = abs_angle,
                distance = dist_p1_hole  -- 存储P1的距离
            })
        end
    end
    
    -- 无候选，返回未命中
    if #candidates == 0 then
        return {is_hit=false, hit_hole=nil,angle=nil,distance=nil}
    end
    
    -- 候选排序：先按角度，再按到P1的距离
    table.sort(candidates, function(a, b)
        if a.angle ~= b.angle then
            return a.angle < b.angle
        else
            return a.distance < b.distance
        end
    end)
    
    -- 角度相近时选距离更近的
    local best = candidates[1]
    local candidates2={}
    if #candidates >= 2 then
        for i=1,#candidates do
            local angle_diff = math.abs(best.angle-candidates[i].angle)
            if angle_diff<= SCREW_CONFIG.ANGLE_DIFF_THRESHOLD then
                table.insert(candidates2,candidates[i])
            else
                break
            end
        end
        if #candidates2>1 then
            table.sort(candidates2,function (a,b)
                return a.distance<b.distance  
            end)
            best=candidates2[1]
        end
    end
    
    return {
        is_hit = true,
        hit_hole = best.index,
        angle = best.angle,
        distance = best.distance
    }
end

function Check_Continuous_Alignment(detect_result, current_hole)
    -- 更新滑动窗口
    if detect_result.is_hit then
        table.insert(alignment_window, detect_result.hit_hole)
    else
        table.insert(alignment_window,-1)
    end
    
    
    -- 保持窗口大小
    while #alignment_window > SCREW_CONFIG.WINDOW_SIZE do
        table.remove(alignment_window, 1)
    end
    
    local hit_count={}
    local current_hit_state=0

    for _ , hit in ipairs(alignment_window) do
        hit_count[hit]=(hit_count[hit] or 0) + 1
    end

    LOG.warn(TableToString(hit_count))

    for key,value in pairs(hit_count) do
        if value>=SCREW_CONFIG.HIT_THRESHOLD and key ~= -1 then
            if key == current_hole then
                current_hit_state=1
            else
                current_hit_state=2
            end
            hit_aaaa=key
        end
    end


    -- 窗口大小足够 且 命中次数达到阈值
    if  current_hit_state==1 then
        alignment_window = {}
        return true, nil
    elseif  current_hit_state==2 then
        return false,true
    end

    return false, nil
end

function Get_center_Point(objbounding)
    local left =objbounding.left
    local right =objbounding.right
    local bottom = objbounding.bottom
    local top = objbounding.top
    local center_x = (left+right)/2
    local center_y = (bottom+top)/2
    return center_x,center_y
end

--写回原来的json表格
function TableToString(t)
	local parts= {}
	for k,v in pairs(t) do
		local keyStr = type(k) == "string" and string.format('[%q]',k) or tostring(k)
		local valStr = type(v) == "string" and string.format('%q',v) or tostring(v)
		table.insert(parts,keyStr.."="..valStr)
	end
	return "{"..table.concat(parts,",").."}"
end

--通过放射变换获取孔的中心点，自定义一个以这个点为中心的roi矩形
function Get_roi(x,y)
    local center_x,center_y = x,y
    local left = center_x - SCREW_CONFIG.ROI_SIZE/2
    local right = center_x + SCREW_CONFIG.ROI_SIZE/2
    local bottom = center_y - SCREW_CONFIG.ROI_SIZE/2
    local top = center_y + SCREW_CONFIG.ROI_SIZE/2
    return {left,bottom,right,top}
end

