RunScript_b6ca7bcc6e804912836429efaf28b762= {}

local tool_name = 'DLObjDetect6'  -- 需访问的工具名
local class_name = '电转枪'  -- 需检测的类别名
local required_count = 20    -- 需要累计的总数
local total_count = 0         -- 累计总数

local overlap_threshold=0.8 -- 交集面积阈值

--固定ROI区域
local ROI_Region={left=221,bottom=737,right=298,top=650}

--初始化函数（初始化历史记录）
function RunScript_b6ca7bcc6e804912836429efaf28b762.setup(this, ctx)
    total_count = 0
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

    return inter_area / area1
end

--执行函数
function RunScript_b6ca7bcc6e804912836429efaf28b762.exec(this, ctx)
    local tool = ctx:get_tool_by_name(tool_name)
    
    if tool == nil then
        return 1, 'Cannot find ' .. tool_name
    end

    local result = tool:result()
    
    -- 直接计数并累加
    for i, obj in ipairs(result) do
        if obj.class_name == class_name and overlap_ratio(obj.bounding,ROI_Region)>overlap_threshold then
            total_count = total_count + 1
        end
    end

    if total_count >= required_count then
        return 0, 'DONE: '.. class_name ..' x'.. total_count
    else
        return 1, 'PROGRESS: '.. total_count ..'/'.. required_count
    end
end

function RunScript_b6ca7bcc6e804912836429efaf28b762.cleanup(this, ctx)
    total_count = 0
end

function RunScript_b6ca7bcc6e804912836429efaf28b762.on_process_begin(this, ctx)
    total_count = 0
end

function RunScript_b6ca7bcc6e804912836429efaf28b762.on_process_end(this, ctx)
    total_count = 0
end
