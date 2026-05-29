RunScript_5f98a059826346a38c655e2191854229= {}

local tool_name = 'DLObjDetect1'  -- 需访问的工具名
local class_name1 = '绝缘保护片_无'  -- 需检测的类别名
local class_name2 = '绝缘保护片_有'  -- 需检测的类别名
local statu_current = 0 -- 当前状态，0：无，1：有

--x分割线
local x_line_threshold = 350

function RunScript_5f98a059826346a38c655e2191854229.setup(this, ctx)
    statu_current = 0
end

function RunScript_5f98a059826346a38c655e2191854229.exec(this, ctx)
    local tool = ctx:get_tool_by_name(tool_name)
    
    if tool == nil then
        return 1, 'Cannot find ' .. tool_name
    end

    local result = tool:result()
    
    -- 直接计数并累加
    for i, obj in ipairs(result) do
        if (obj.class_name == class_name1 or obj.class_name == class_name2) and obj.bounding.right < x_line_threshold then
            if obj.class_name == class_name1 then
                statu_current = 0
            else
                statu_current = 1
            end
        end
    end

    if statu_current == 1 then
        return 0, 'DONE: '.. class_name2
    else
        return 1, 'PROGRESS: '.. class_name1
    end
end

function RunScript_5f98a059826346a38c655e2191854229.cleanup(this, ctx)
    statu_current = 0
end

function RunScript_5f98a059826346a38c655e2191854229.on_process_begin(this, ctx)
    statu_current = 0    
end

function RunScript_5f98a059826346a38c655e2191854229.on_process_end(this, ctx)
    statu_current = 0 
end


