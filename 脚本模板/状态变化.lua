RunScript_25fbb148_8e24_4aff_8928_24faa8ae4f29 = {}

local tool_name = 'DLObjDetect'
local class_name1 = '剪刀合'
local class_name2 = '剪刀开'
local last_state = 0      -- 上一次状态
local cycle_count = 0     -- 已完成的变化次数
local required_cycles = 5 -- 需完成的变化次数

function RunScript_25fbb148_8e24_4aff_8928_24faa8ae4f29.setup(this, ctx)
    last_state = 0
    cycle_count = 0
end

function RunScript_25fbb148_8e24_4aff_8928_24faa8ae4f29.exec(this, ctx)

    local tool = ctx:get_tool_by_name(tool_name)
    
    if tool == nil then
        return 1, 'Cannot find ' .. tool_name
    end

    local result = tool:result()

    for i, obj in ipairs(result) do
        if obj.class_name == class_name1 then
            if last_state == 2 then
                cycle_count = cycle_count + 1
            end
            last_state = 1
        elseif obj.class_name == class_name2 then
            last_state = 2
        end
    end

    if cycle_count >= required_cycles then
        return 0, 'DONE: cycles x'.. cycle_count
    else
        return 1, 'CYCLES: '.. cycle_count ..'/'.. required_cycles
    end

end

function RunScript_25fbb148_8e24_4aff_8928_24faa8ae4f29.cleanup(this, ctx)
    last_state = 0
    cycle_count = 0
end

function RunScript_25fbb148_8e24_4aff_8928_24faa8ae4f29.on_process_begin(this, ctx)
    last_state = 0
    cycle_count = 0
end

function RunScript_25fbb148_8e24_4aff_8928_24faa8ae4f29.on_process_end(this, ctx)
    last_state = 0
    cycle_count = 0
end