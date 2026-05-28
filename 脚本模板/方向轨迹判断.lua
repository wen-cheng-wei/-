RunScript_6494dd07_5df3_4d8b_a089_58e199a4968c = {}

-- ==================== 配置参数 ====================
local tool_name = 'DLObjDetect1'
local target_class = 'PCB1_旋转90度'

-- ★ 动作序列：按顺序定义，每个动作 { angle = 方向角度, frames = 需要累积帧数 }
--    向右 = 0,   向上 = -90,   向左 = 180,   向下 = 90
local motion_sequence = {
    { angle = 0, frames = 10 },   -- 第1步：向右
    { angle = 180, frames = 10 },   -- 第2步：向左
    { angle = 0, frames = 10 },   -- 第1步：向右
    { angle = -90, frames = 8  },   -- 第3步：向上
    { angle = 90,  frames = 10 },   -- 第4步：向下
}

local angle_tolerance = 45            -- 角度容差(度)
local min_displacement = 10           -- 最小位移(像素)
local reduce_score = 1                -- 方向不对时扣几分

-- ==================== 状态变量 ====================
local prev_center = nil
local current_stage = 1               -- 当前在第几步（从1开始）
local stage_count = 0                 -- 当前阶段的连续计数
local success_triggered = false

-- ==================== 生命周期 ====================
function RunScript_6494dd07_5df3_4d8b_a089_58e199a4968c.setup(this, ctx)
end

function RunScript_6494dd07_5df3_4d8b_a089_58e199a4968c.cleanup(this, ctx)
end

function RunScript_6494dd07_5df3_4d8b_a089_58e199a4968c.on_process_begin(this, ctx)
    prev_center = nil
    current_stage = 1
    stage_count = 0
    success_triggered = false
end

function RunScript_6494dd07_5df3_4d8b_a089_58e199a4968c.on_process_end(this, ctx)
    prev_center = nil
    current_stage = 1
    stage_count = 0
    success_triggered = false
end

-- ==================== 辅助函数 ====================
local function get_target_object(result)
    for _, obj in ipairs(result) do
        if obj.class_name == target_class and obj.bounding then
            return obj
        end
    end
    return nil
end

local function get_center(bbox)
    return {
        x = (bbox.left + bbox.right) / 2,
        y = (bbox.top + bbox.bottom) / 2
    }
end

local function calc_angle_diff(angle, target)
    local diff = math.abs(angle - target)
    if diff > 180 then
        diff = 360 - diff
    end
    return diff
end

local function get_stage_name(angle)
    local names = {
        [0] = "Right", [-90] = "Up", [180] = "Left", [90] = "Down"
    }
    return names[angle] or ("Angle:" .. angle)
end

-- ==================== 主逻辑 ====================
function RunScript_6494dd07_5df3_4d8b_a089_58e199a4968c.exec(this, ctx)
    -- 已经全部完成，直接返回成功
    if success_triggered then
        return 0, 'Sequence completed: ' .. target_class
    end

    local tool = ctx:get_tool_by_name(tool_name)
    if tool == nil then
        return 1, 'Cannot find ' .. tool_name
    end

    local result = tool:result()
    if not result or #result == 0 then
        prev_center = nil
        return 1, 'No objects detected | Stage ' .. current_stage .. '/' .. #motion_sequence .. ' [' .. get_stage_name(motion_sequence[current_stage].angle) .. '] count: ' .. stage_count .. '/' .. motion_sequence[current_stage].frames
    end

    local target_obj = get_target_object(result)
    if not target_obj then
        prev_center = nil
        return 1, 'Target not found | Stage ' .. current_stage .. '/' .. #motion_sequence .. ' [' .. get_stage_name(motion_sequence[current_stage].angle) .. '] count: ' .. stage_count .. '/' .. motion_sequence[current_stage].frames
    end

    local current_center = get_center(target_obj.bounding)

    if prev_center then
        local dx = current_center.x - prev_center.x
        local dy = current_center.y - prev_center.y
        local distance = math.sqrt(dx * dx + dy * dy)

        if distance >= min_displacement then
            local angle = math.deg(math.atan(dy, dx))
            local target_angle = motion_sequence[current_stage].angle
            local angle_diff = calc_angle_diff(angle, target_angle)

            if angle_diff <= angle_tolerance then
                -- 方向匹配当前阶段，加分
                stage_count = stage_count + 1

                -- 检查当前阶段是否达标
                if stage_count >= motion_sequence[current_stage].frames then
                    if current_stage >= #motion_sequence then
                        -- 所有阶段完成
                        success_triggered = true
                        prev_center = current_center
                        return 0, 'Sequence completed: ' .. target_class
                    else
                        -- 进入下一阶段
                        current_stage = current_stage + 1
                        stage_count = 0
                    end
                end
            else
                -- 方向不对，扣当前阶段的分（不低于0）
                stage_count = math.max(0, stage_count - reduce_score)
            end
        end
    end

    prev_center = current_center

    return 1, 'Stage ' .. current_stage .. '/' .. #motion_sequence .. ' [' .. get_stage_name(motion_sequence[current_stage].angle) .. '] count: ' .. stage_count .. '/' .. motion_sequence[current_stage].frames
end
