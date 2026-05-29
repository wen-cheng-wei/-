RunScript_e934138a_7f60_47ef_bbbb_4daf007bf8f0= {}

local tool_name = 'DLObjDetect7'  -- 需访问的工具名
local class_name = '材料2'  -- 需检测的类别名
local required_count = 30    -- 需要累计的总数
local total_count = 0         -- 累计总数

function RunScript_e934138a_7f60_47ef_bbbb_4daf007bf8f0.setup(this, ctx)
    total_count = 0
end

function RunScript_e934138a_7f60_47ef_bbbb_4daf007bf8f0.exec(this, ctx)
    local tool = ctx:get_tool_by_name(tool_name)
    
    if tool == nil then
        return 1, 'Cannot find ' .. tool_name
    end

    local result = tool:result()
    
    -- 直接计数并累加
    for i, obj in ipairs(result) do
        if obj.class_name == class_name then
            total_count = total_count + 1
        end
    end

    if total_count >= required_count then
        return 0, 'DONE: '.. class_name ..' x'.. total_count
    else
        return 1, 'PROGRESS: '.. total_count ..'/'.. required_count
    end
end

function RunScript_e934138a_7f60_47ef_bbbb_4daf007bf8f0.cleanup(this, ctx)
    total_count = 0
end

function RunScript_e934138a_7f60_47ef_bbbb_4daf007bf8f0.on_process_begin(this, ctx)
    total_count = 0
end

function RunScript_e934138a_7f60_47ef_bbbb_4daf007bf8f0.on_process_end(this, ctx)
    total_count = 0
end
