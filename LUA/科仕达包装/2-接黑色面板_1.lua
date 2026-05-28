RunScript_09b7782c_4bea_459c_bc2e_1626736d7ecc= {}

local tool_name = 'DLObjDetect2'  -- 需访问的工具名
local class_name = '2-接黑色面板_1'  -- 需检测的类别名
local required_count = 10    -- 需要累计的总数
local total_count = 0         -- 累计总数

function RunScript_09b7782c_4bea_459c_bc2e_1626736d7ecc.setup(this, ctx)
    total_count = 0
end

function RunScript_09b7782c_4bea_459c_bc2e_1626736d7ecc.exec(this, ctx)
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

function RunScript_09b7782c_4bea_459c_bc2e_1626736d7ecc.cleanup(this, ctx)
    total_count = 0
end

function RunScript_09b7782c_4bea_459c_bc2e_1626736d7ecc.on_process_begin(this, ctx)
    total_count = 0
end

function RunScript_09b7782c_4bea_459c_bc2e_1626736d7ecc.on_process_end(this, ctx)
    total_count = 0
end
