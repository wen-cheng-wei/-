RunScript_25fbb148_8e24_4aff_8928_24faa8ae4f25 = {}

-- 配置参数
local class_name = ""        -- 需要检测的标签名称
local tool_name = ""         -- 对象检测工具名称
local alarm_tool_name = ""   -- 报警工具名称（可选）

-- 四个矩形ROI区域定义（左下、右上、右下、左上）
-- 格式: {left=左边界, bottom=下边界, right=右边界, top=上边界}
local ROIs = {
    {left=100,  bottom=500, right=300, top=300},   -- ROI 1: 左下区域
    {left=700,  bottom=500, right=900, top=300},   -- ROI 2: 右下区域
    {left=100,  bottom=200, right=300, top=50},    -- ROI 3: 左上区域（正确区域）
    {left=700,  bottom=200, right=900, top=50}     -- ROI 4: 右上区域
}

-- 指定正确的区域索引（从1开始）
local correct_roi_index = 3  -- 第3个区域（左上）是正确区域

-- 连续检测成功次数配置
local detection_history = {
    results = {}, max_size = 100, Required_Consecutive = 10
}

-- 报警历史记录
local alarm_history = {
    results = {}, max_size = 100, Required_Consecutive = 5
}

-- 交并比阈值（判断物体是否在区域内）
local overlap_threshold = 0.5

function RunScript_25fbb148_8e24_4aff_8928_24faa8ae4f25.setup(this, ctx)
end

-- 计算交并比
local function overlap_ratio(box1, box2)
    local x1, y1, x2, y2 = box1.left, box1.bottom, box1.right, box1.top
    local x3, y3, x4, y4 = box2.left, box2.bottom, box2.right, box2.top
    
    local left = math.max(x1, x3)
    local right = math.min(x2, x4)
    local bottom = math.min(y1, y3)
    local top = math.max(y2, y4)
    
    local inter_w = right - left
    local inter_h = bottom - top
    local inter_area = 0
    if inter_w > 0 and inter_h > 0 then
        inter_area = inter_w * inter_h
    end
    
    local area1 = (x2 - x1) * (y1 - y2)
    local area2 = (x4 - x3) * (y3 - y4)
    local union_area = area1 + area2 - inter_area
    
    if union_area <= 0 then
        return 0
    end
    
    return inter_area / union_area
end

-- 判断物体位于哪个ROI区域
local function find_object_roi(obj_bounding)
    for i, roi in ipairs(ROIs) do
        if overlap_ratio(obj_bounding, roi) >= overlap_threshold then
            return i  -- 返回区域索引
        end
    end
    return nil  -- 不在任何区域内
end

-- 计算连续成功次数
local function count_consecutive_success(history)
    local consecutive = 0
    for i = #history.results, 1, -1 do
        if history.results[i] then
            consecutive = consecutive + 1
        else
            break
        end
    end
    return consecutive
end

-- 记录历史
local function record_history(history, success)
    table.insert(history.results, success)
    if #history.results > history.max_size then
        table.remove(history.results, 1)
    end
end

function RunScript_25fbb148_8e24_4aff_8928_24faa8ae4f25.exe(this, ctx)
    local tool = ctx:get_tool_by_name(tool_name)
    if tool == nil then
        record_history(detection_history, false)
        return 1, 'Cannot find tool: ' .. tool_name
    end
    
    local result = tool:results()
    if result == nil then
        record_history(detection_history, false)
        return 1, 'Tool result is nil'
    end
    
    local current_success = false
    local alarm_flag = false
    
    -- 检测每个识别到的物体
    for _, obj in ipairs(result) do
        if obj.class_name == class_name and obj.bounding then
            local roi_index = find_object_roi(obj.bounding)
            
            if roi_index == correct_roi_index then
                -- 物体在正确的区域
                current_success = true
            elseif roi_index ~= nil then
                -- 物体在错误的区域，触发报警
                alarm_flag = true
            end
        end
    end
    
    -- 记录历史
    record_history(detection_history, current_success)
    record_history(alarm_history, alarm_flag)
    
    -- 检查连续成功或报警
    local consecutive_detection = count_consecutive_success(detection_history)
    local consecutive_alarm = count_consecutive_success(alarm_history)
    
    -- 连续报警触发
    if consecutive_alarm >= alarm_history.Required_Consecutive then
        if alarm_tool_name ~= "" then
            local alarm_tool = ctx:get_tool_by_name(alarm_tool_name)
            if alarm_tool ~= nil then
                alarm_tool:exec(ctx)
            end
        end
        return 2, 'Error: Object in wrong ROI'
    end
    
    -- 连续检测成功
    if consecutive_detection >= detection_history.Required_Consecutive then
        return 0, 'Successful: Object in correct ROI'
    end
    
    -- 继续检测
    if current_success then
        return 3, 'Detecting: Object in correct ROI'
    else
        return 3, 'Detecting: Waiting for object'
    end
end

function RunScript_25fbb148_8e24_4aff_8928_24faa8ae4f25.clear(this, ctx)
end

function RunScript_25fbb148_8e24_4aff_8928_24faa8ae4f25.on_process_begin(this, ctx)
    detection_history.results = {}
    alarm_history.results = {}
end

function RunScript_25fbb148_8e24_4aff_8928_24faa8ae4f25.on_process_end(this, ctx)
    detection_history.results = {}
    alarm_history.results = {}
end