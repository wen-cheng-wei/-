--[[该流程检测CCS1和CCS2是否有顺序防反，物品放反的的情况
ccs1通过检测锁扣来定位他是否有放错，只要其锁扣位置超过水平线y=n以下就NG,或者是在不对的位置也会NG
ccs2通过检测定位局部区域来检测是否有错放，只有在位置3是OK的
注意点：顺序不能反，因此工序1如果检测到CCS2的局部区域出现在第三个点中且没有CCS1锁扣在位置1存在报NG，防止工序2完成之后直接到工序1而直接报警
        工序2结束后会立即重置到第一个流程，因此第一个流程在锁扣和ccs2均处于出现在相应位置时候不能报警
]]

RunScript_c91c1fb3_949c_43be_b1b1_0dc1e658e7a8 = {}

-- 该表用于记录是否成功返回
local detection_history = {
results = {}, max_size = 100, Required_Consecutive =10 -- 需要连续成功的次数
}

--该表用来记录是否做错报警
local alarm_history={
results = {}, max_size = 100, Required_Consecutive =5 -- 需要连续成功的次数
}

--检测CCS1锁扣区域,左下、右上,第一个为正确位置，其余均为错误位置
local CCS1_Region={{left=562,bottom=659,right=945,top=447},
{left=1814,bottom=1169,right=2195,top=938},
{left=567,bottom=1402,right=855,top=1238},
{left=1814,bottom=1874,right=2195,top=1676}}

--检测CCS2区域,左下、右上，第三个为正确位置，其余均为错误位置
local CCS2_Region={{left=738,bottom=1590,right=943,top=1438},
{left=1797,bottom=919,right=2060,top=687},
{left=728,bottom=1654,right=950,top=1435},
{left=1812,bottom=1666,right=2031,top=1416}}

--锁扣水平线
local Y_Horizon=847
--交并比阈值
local overlap_threshold=0.5
--标签名字
local label={"CCS1","CCS2"}

--对象工具名称
local tool_name='DLObjDetect1'
--关闭报警工具
local alarm_tool1='AlarmControl1'
local alarm_tool2='AlarmControl2'
--开启报警工具
local alarm_tool3='AlarmControl3'
local alarm_tool4='AlarmControl4'
--时间设定
local start_time=os.time()
local alarm_time_limit=20 --连续检测超过alarm_time_limit秒触发报警

-- 记录历史函数
local function record_history(history,success)
    local entry = {
        timestamp = os.time(), success = success
    }
    table.insert(history.results, entry) -- 限制历史记录大小
    if #history.results > history.max_size then
        table.remove(history.results, 1)
    end
end

-- 只找当前工序的连续成功次数（从最新记录开始）
local function count_consecutive_success(history)
    local consecutive = 0
    for i = #history.results, 1, -1 do
        if history.results[i].success then
            consecutive = consecutive + 1
        else
            break
        end
    end
    return consecutive
end

--返回交并比,输入左下角，右上角坐标
local function overlap_ratio(box1,box2)
    local x1=box1.left
    local y1=box1.bottom
    local x2=box1.right
    local y2=box1.top
    local x3=box2.left
    local y3=box2.bottom
    local x4=box2.right
    local y4=box2.top
    -- 计算交集区域
    local left   = math.max(x1, x3)
    local right  = math.min(x2, x4)
    local bottom = math.min(y1, y3)
    local top    = math.max(y2, y4)

    -- 计算交集面积
    local inter_w = right - left
    local inter_h = bottom - top
    local inter_area = 0
    if inter_w > 0 and inter_h > 0 then
        inter_area = inter_w * inter_h
    else
        inter_area=0
    end

    -- 计算各自面积
    local area1 = (x2 - x1) * (y1 - y2)
    local area2 = (x4 - x3) * (y3 - y4)

    -- 并集面积
    local union_area = area1 + area2 - inter_area

    -- 避免除零
    if union_area <= 0 then
        return 0
    end

    return inter_area / union_area
end

--返回中心点
local function Center_Point(region)
    local center_x=(region.left+region.right)/2
    local center_y=(region.bottom+region.top)/2
    return center_x,center_y
end

--初始化函数（初始化历史记录）
function RunScript_c91c1fb3_949c_43be_b1b1_0dc1e658e7a8.setup(this, ctx)
    detection_history.results = {}
    alarm_history.results={}
end

--执行函数
function RunScript_c91c1fb3_949c_43be_b1b1_0dc1e658e7a8.exec(this, ctx)
    --超时报警
    local end_time=os.time()
    local spend_time=end_time-start_time
    local tool1 =ctx:get_tool_by_name(alarm_tool3)
    local tool2 =ctx:get_tool_by_name(alarm_tool4)
    if spend_time>alarm_time_limit then
        tool1:exec(ctx)
        tool2:exec(ctx)
    end

    local tool = ctx:get_tool_by_name(tool_name)
    if tool == nil then
        record_history(detection_history,false)
        return 1, 'Cannot find ' .. tool_name
    end

    -- 获取当前检测结果
    local result = tool:result()
    --只记录是否成功,用来判断是否跳转流程
    local CCS_success={false,false}
    local current_success=false
    --记录是否满足报警条件，判断是否报警
    local Alarm_flag=false
    -- 统计当前检测到的某类别数量
    for _, obj in ipairs(result) do
        if obj.class_name == label[1] then
           for i,region in ipairs(CCS1_Region) do
            if overlap_ratio(obj.bounding,region)>=overlap_threshold then
                if i==1 then
                    CCS_success[1]=true
                else
                    Alarm_flag=true
                end
            end
           end
           local _,center_y=Center_Point(obj.bounding)
           if center_y>Y_Horizon then
                Alarm_flag=true
           end
        elseif obj.class_name == label[2] then
            for j,region2 in ipairs(CCS2_Region) do
                if overlap_ratio(obj.bounding,region2)>=overlap_threshold then
                    if j==3 then
                        CCS_success[2]=true
                    else
                        Alarm_flag=true
                    end
                end
            end
        end
    end

    if CCS_success[1] and CCS_success[2] then
        Alarm_flag=false
    elseif CCS_success[1] and CCS_success[2]==false then
        current_success=true
        Alarm_flag=false
    elseif CCS_success[1]==false and CCS_success[2] then
        Alarm_flag=true
    end
    

   
    -- 记录当前数据到历史
    record_history(detection_history,current_success)
    record_history(alarm_history,Alarm_flag)
    local consecutive_detection_success = count_consecutive_success(detection_history)
    local consecutive_alarm_success = count_consecutive_success(alarm_history)

    if consecutive_detection_success >= detection_history.Required_Consecutive then
        return 0,'Successful'
    end

    if  consecutive_alarm_success >= alarm_history.Required_Consecutive  then
        tool1:exec(ctx)
        tool2:exec(ctx)
        return 2, 'Error'
    end

    return 3,'pass'
end

function RunScript_c91c1fb3_949c_43be_b1b1_0dc1e658e7a8.cleanup(this, ctx)
    detection_history.results = {}
end



function RunScript_c91c1fb3_949c_43be_b1b1_0dc1e658e7a8.on_process_begin(this, ctx)
	detection_history.results = {}
    alarm_history.results={}
    local tool1 =ctx:get_tool_by_name(alarm_tool1)
    local tool2 =ctx:get_tool_by_name(alarm_tool2)
    tool1:exec(ctx)
    tool2:exec(ctx)
    start_time=os.time()
end

function RunScript_c91c1fb3_949c_43be_b1b1_0dc1e658e7a8.on_process_end(this, ctx)
	detection_history.results = {}
    alarm_history.results={}
    start_time=os.time()
end
