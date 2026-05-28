RunScript_5e998515_5f68_46cb_b79a_9568dc448992 = {}

local tool_name = 'DLObjDetect'  -- 需访问的工具名
local class_name = '按压平顺'  -- 需检测的类别名
local detection_history = { results = {}, max_size = 100, required_consecutive = 20 }

function RunScript_5e998515_5f68_46cb_b79a_9568dc448992.setup(this, ctx)
    detection_history.results = {}
end


function RunScript_5e998515_5f68_46cb_b79a_9568dc448992.exec(this, ctx)

    local tool = ctx:get_tool_by_name(tool_name)
    
    if tool == nil then
        record_history(false, 0, "tool is not found")
        return 1, 'Cannot find ' .. tool_name
    end

    local result = tool:result()

    local current_count = 0
    local current_success = false

    for i, obj in ipairs(result) do
        if obj.class_name == class_name then
            current_count = current_count + 1
            current_success = true
        end

    end

    record_history(current_success, current_count, current_success and 'Found '..current_count..' ' .. class_name or "did not find " .. class_name)

    local consecutive_success = count_consecutive_success()

    if consecutive_success >= detection_history.required_consecutive then
        return 0, 'DONE: '.. class_name ..' x'.. consecutive_success
    else
        if current_success then
            return 3, 'PROGRESS: '.. consecutive_success ..'/'.. detection_history.required_consecutive
        else
            return 2, 'MISS: '.. consecutive_success ..'/'.. detection_history.required_consecutive
        end
    end

end

function record_history(success, count, message)

    local entry = {
        timestamp = os.time(), success = success, count = count, message = message
    }

    table.insert(detection_history.results, entry)

    if #detection_history.results > detection_history.max_size then
        table.remove(detection_history.results, 1)
    end

end

function count_consecutive_success()
    
    local consecutive = 0
    for i = #detection_history.results, 1, -1 do
        if detection_history.results[i].success then
            consecutive = consecutive + 1
        else
            break 
        end
    end
    return consecutive
end

function RunScript_5e998515_5f68_46cb_b79a_9568dc448992.cleanup(this, ctx)
    detection_history.results = {}
end

function RunScript_5e998515_5f68_46cb_b79a_9568dc448992.on_process_begin(this, ctx)
	detection_history.results = {}
end

function RunScript_5e998515_5f68_46cb_b79a_9568dc448992.on_process_end(this, ctx)
	detection_history.results = {}
end