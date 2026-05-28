RunScript_05301e48343e41699f2cd37406a45a2d = {}

-- 检测凹起区域,左下、右上
local tool_name = 'DLObjDetect8'
local class_name1 = '指示拉片'
local class_name2 = '调节旋钮'
local regions = {}
local regions_max = 20
local intersections_num = 0
local success_intersection_num = 20
local flag = 0

function RunScript_05301e48343e41699f2cd37406a45a2d.setup(this, ctx)

end

function RunScript_05301e48343e41699f2cd37406a45a2d.exec(this, ctx)
    local tool = ctx:get_tool_by_name(tool_name)
    if tool == nil then
        return 1, 'Cannot find ' .. tool_name
    end

    local result = tool:result()
    if not result or #result == 0 then
        return 1, 'No objects detected'
    end

    for _, obj in ipairs(result) do
        if obj.class_name == class_name1 and obj.bounding then
            Add_Region(regions, obj.bounding.left, obj.bounding.bottom, obj.bounding.right, obj.bounding.top)
        end
    end
    
    if #regions ~= 0 then
        for _, obj in ipairs(result) do
            if obj.class_name == class_name2 and obj.bounding then
                for _, obj2 in ipairs(regions) do
                    if Overlap_Ratio(obj.bounding, obj2)>0 then
                        intersections_num=intersections_num+1
                        flag = 1
                    end
                    if flag == 1 then
                        flag = 2
                        break
                    end
                end
            end
        end
    end

    if intersections_num>success_intersection_num then
        return 0, 'Success: ' .. class_name1 .. ' intersects ' .. class_name2
    end

    return 1, 'No intersection between ' .. class_name1 .. ' and ' .. class_name2 .. ' (' .. class_name1 .. ' status: ' .. (#regions~=0 and 'Yes' or 'No') .. ')'
end

function RunScript_05301e48343e41699f2cd37406a45a2d.cleanup(this, ctx)
end

function RunScript_05301e48343e41699f2cd37406a45a2d.on_process_begin(this, ctx)
    intersections_num = 0
    regions = {}
end

function RunScript_05301e48343e41699f2cd37406a45a2d.on_process_end(this, ctx)
    intersections_num = 0
    regions = {}
end


function Clean_Tu_Regions()
    while #regions >= regions_max do
        table.remove(regions, 1)
    end
end


function Add_Region(regions, left, bottom, right, top)
    if not left or not bottom or not right or not top then
        return
    end
    local temp_region = { left = left, bottom = bottom, right = right, top = top }
    table.insert(regions, temp_region)
    Clean_Tu_Regions()
end

function Is_overlap(box1, box2)
    if box1.right < box2.left or
       box1.left > box2.right or
       box1.top > box2.bottom or
       box1.bottom < box2.top then
        return false
    end
    return true
end

function Overlap_Ratio(box1, box2)
    -- 计算交集区域
    local left   = math.max(box1.left, box2.left)
    local right  = math.min(box1.right, box2.right)
    local bottom = math.min(box1.bottom, box2.bottom)
    local top    = math.max(box1.top, box2.top)
    
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
    local area1 = (box1.right - box1.left) * (box1.bottom - box1.top)
    local area2 = (box2.right - box2.left) * (box2.bottom - box2.top)
    
    -- 并集面积
    local union_area = area1 + area2 - inter_area
    
    -- 避免除零
    if union_area <= 0 then
        return 0
    end
    
    return inter_area / union_area
end