RunScript_5f94a6044a7a4b59a6f0a30568a9b53e= {}

local tool_name = 'DLObjDetect10'  -- 需访问的工具名
local class_name = '盖子'  -- 需检测的类别名
local required_count = 50    -- 需要累计的总数
local total_count = 0         -- 累计总数

function RunScript_5f94a6044a7a4b59a6f0a30568a9b53e.setup(this, ctx)
    total_count = 0
end

function RunScript_5f94a6044a7a4b59a6f0a30568a9b53e.exec(this, ctx)
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

function RunScript_5f94a6044a7a4b59a6f0a30568a9b53e.cleanup(this, ctx)
    total_count = 0
end

function RunScript_5f94a6044a7a4b59a6f0a30568a9b53e.on_process_begin(this, ctx)
    total_count = 0
end

function RunScript_5f94a6044a7a4b59a6f0a30568a9b53e.on_process_end(this, ctx)
    total_count = 0
end
