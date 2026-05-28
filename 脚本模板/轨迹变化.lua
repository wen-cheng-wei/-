RunScript_ff264eb1_4816_4077_b7ac_107f63603ae1 = {}

-- ============================================================
-- 配置参数
-- ============================================================
local tool_name = 'DLObjDetect2'
local target_class = 'PCB1_旋转90度'
-- 拟合参数
local min_points_for_fit = 10      -- 最少需要多少点才能拟合
local max_fit_error = 0.15         -- 最大拟合误差（15%）
local required_circle_count = 4    -- 需要连续几次拟合为圆形才算成功
-- 运动参数
local min_displacement = 3         -- 最小位移（过滤抖动）
local history_max_size = 50        -- 最多保存50个点
-- 方向检测参数
-- 方向选项: 'clockwise'(顺时针), 'counterclockwise'(逆时针), 'both'(两者都行)
local required_direction = 'counterclockwise'  -- 要求顺时针旋转
local min_angle_span = 270        -- 最小角度跨度（度），用于判断完整旋转

-- ============================================================
-- 内部变量
-- ============================================================
local trajectory_points = {}       -- 存储轨迹点
local prev_center = nil
local circle_detection_count = 0   -- 连续检测到圆形的次数
local success_triggered = false

-- ============================================================
-- 几何计算函数
-- ============================================================
-- 计算两点之间的距离
local function distance(p1, p2)
    return math.sqrt((p2.x - p1.x)^2 + (p2.y - p1.y)^2)
end

-- 计算两点之间的角度（相对于圆心）
local function calculate_angle(center, point)
    return math.deg(math.atan(point.y - center.y, point.x - center.x))
end

-- 计算两个角度之间的最小差值（考虑360°环绕）
local function angle_difference(a1, a2)
    local diff = a2 - a1
    -- 调整到 -180 到 180 范围
    while diff > 180 do
        diff = diff - 360
    end
    while diff < -180 do
        diff = diff + 360
    end
    return diff
end

-- 判断旋转方向（基于累计角度变化）
local function detect_rotation_direction(angles)
    if #angles < 3 then
        return 'unknown'
    end
    
    local total_rotation = 0
    for i = 2, #angles do
        total_rotation = total_rotation + angle_difference(angles[i-1], angles[i])
    end
    
    if total_rotation > 0 then
        return 'counterclockwise'  -- 逆时针（角度增加）
    elseif total_rotation < 0 then
        return 'clockwise'         -- 顺时针（角度减少）
    else
        return 'unknown'
    end
end

-- 判断方向是否符合要求
local function is_direction_ok(direction)
    if required_direction == 'both' then
        return true
    end
    return direction == required_direction
end

-- 计算三点确定的圆的圆心和半径
local function fit_circle_from_three_points(p1, p2, p3)
    local mid_x1 = (p1.x + p2.x) / 2
    local mid_y1 = (p1.y + p2.y) / 2
    local mid_x2 = (p2.x + p3.x) / 2
    local mid_y2 = (p2.y + p3.y) / 2
    
    local k1 = nil
    local k2 = nil
    
    if p2.x - p1.x ~= 0 then
        k1 = (p2.y - p1.y) / (p2.x - p1.x)
    end
    
    if p3.x - p2.x ~= 0 then
        k2 = (p3.y - p2.y) / (p3.x - p2.x)
    end
    
    local perp_k1 = (k1 and k1 ~= 0) and (-1 / k1) or 0
    local perp_k2 = (k2 and k2 ~= 0) and (-1 / k2) or 0
    
    if k1 == nil then
        local center_x = (p1.x + p2.x) / 2
        if k2 == nil then
            return nil
        end
        local center_y = perp_k2 * (center_x - mid_x2) + mid_y2
        local center = {x = center_x, y = center_y}
        local radius = distance(center, p1)
        return {center = center, radius = radius}
    end
    
    if k2 == nil then
        local center_x = (p2.x + p3.x) / 2
        local center_y = perp_k1 * (center_x - mid_x1) + mid_y1
        local center = {x = center_x, y = center_y}
        local radius = distance(center, p1)
        return {center = center, radius = radius}
    end
    
    if perp_k1 == perp_k2 then
        return nil
    end
    
    local center_x = (perp_k1 * mid_x1 - perp_k2 * mid_x2 + mid_y2 - mid_y1) / (perp_k1 - perp_k2)
    local center_y = perp_k1 * (center_x - mid_x1) + mid_y1
    
    local center = {x = center_x, y = center_y}
    local radius = distance(center, p1)
    
    local r2 = distance(center, p2)
    local r3 = distance(center, p3)
    
    if math.abs(r2 - radius) > 1 or math.abs(r3 - radius) > 1 then
        return nil
    end
    
    return {center = center, radius = radius}
end

-- 多点拟合：取多个三点拟合的平均值
local function fit_circle_from_multiple_points(points)
    if #points < 3 then
        return nil
    end
    
    local circles = {}
    local sample_count = math.min(#points, 20)
    
    for i = 1, sample_count do
        local idx1 = math.random(1, #points)
        local idx2 = math.random(1, #points)
        local idx3 = math.random(1, #points)
        
        while idx2 == idx1 do
            idx2 = math.random(1, #points)
        end
        while idx3 == idx1 or idx3 == idx2 do
            idx3 = math.random(1, #points)
        end
        
        local circle = fit_circle_from_three_points(
            points[idx1], points[idx2], points[idx3]
        )
        
        if circle then
            table.insert(circles, circle)
        end
    end
    
    if #circles == 0 then
        return nil
    end
    
    local avg_x = 0
    local avg_y = 0
    local avg_r = 0
    
    for _, circle in ipairs(circles) do
        avg_x = avg_x + circle.center.x
        avg_y = avg_y + circle.center.y
        avg_r = avg_r + circle.radius
    end
    
    avg_x = avg_x / #circles
    avg_y = avg_y / #circles
    avg_r = avg_r / #circles
    
    return {
        center = {x = avg_x, y = avg_y},
        radius = avg_r
    }
end

-- 计算轨迹与拟合圆的拟合误差
local function calculate_fit_error(points, circle)
    if not circle or #points == 0 then
        return 1
    end
    
    local total_error = 0
    local max_error = 0
    
    for _, p in ipairs(points) do
        local dist = distance(p, circle.center)
        local error = math.abs(dist - circle.radius) / circle.radius
        total_error = total_error + error
        
        if error > max_error then
            max_error = error
        end
    end
    
    local avg_error = total_error / #points
    return avg_error, max_error
end

-- 检查轨迹的角度覆盖范围
local function check_angle_coverage(points, circle)
    if #points < 2 then
        return 0
    end
    
    local angles = {}
    for _, p in ipairs(points) do
        local angle = calculate_angle(circle.center, p)
        table.insert(angles, angle)
    end
    
    -- 找最小和最大角度
    local min_angle = angles[1]
    local max_angle = angles[1]
    for _, angle in ipairs(angles) do
        if angle < min_angle then min_angle = angle end
        if angle > max_angle then max_angle = angle end
    end
    
    local angle_span = max_angle - min_angle
    return angle_span
end

-- ============================================================
-- 辅助函数
-- ============================================================
local function get_object_center(obj)
    if obj and obj.bounding then
        local bbox = obj.bounding
        return {
            x = (bbox.left + bbox.right) / 2,
            y = (bbox.top + bbox.bottom) / 2
        }
    end
    return nil
end

--添加轨迹点并维护历史记录大小
local function add_trajectory_point(point)
    table.insert(trajectory_points, {x = point.x, y = point.y})
    
    while #trajectory_points > history_max_size do
        table.remove(trajectory_points, 1)
    end
end

-- 清除轨迹数据
local function clear_trajectory()
    trajectory_points = {}
    circle_detection_count = 0
end

-- 获取方向的中文名称
local function get_direction_name(direction)
    if direction == 'clockwise' then
        return '顺时针'
    elseif direction == 'counterclockwise' then
        return '逆时针'
    else
        return '未知'
    end
end

-- ============================================================
-- 主执行函数
-- ============================================================
function RunScript_ff264eb1_4816_4077_b7ac_107f63603ae1.setup(this, ctx)
    clear_trajectory()
    prev_center = nil
    success_triggered = false
end

function RunScript_ff264eb1_4816_4077_b7ac_107f63603ae1.exec(this, ctx)
    local tool = ctx:get_tool_by_name(tool_name)
    if tool == nil then
        return 1, 'Cannot find ' .. tool_name
    end
    
    local result = tool:result()
    if not result or #result == 0 then
        clear_trajectory()
        prev_center = nil
        return 1, 'No objects detected'
    end
    
    local target_obj = nil
    for _, obj in ipairs(result) do
        if obj.class_name == target_class and obj.bounding then
            target_obj = obj
            break
        end
    end
    
    if not target_obj then
        clear_trajectory()
        prev_center = nil
        return 1, 'Target not found: ' .. target_class
    end
    
    local current_center = get_object_center(target_obj)
    if not current_center then
        return 1, 'Cannot get center point'
    end
    
    if prev_center then
        local move_dist = distance(prev_center, current_center)
        if move_dist >= min_displacement then
            add_trajectory_point(current_center)
        end
    else
        add_trajectory_point(current_center)
    end
    
    prev_center = current_center
    
    local status_msg = ""
    
    if #trajectory_points >= min_points_for_fit then
        local fitted_circle = fit_circle_from_multiple_points(trajectory_points)
        
        if fitted_circle then
            local avg_error, max_error = calculate_fit_error(trajectory_points, fitted_circle)
            
            status_msg = string.format("Points: %d, Radius: %.1f, Error: %.1f%%", 
                         #trajectory_points, fitted_circle.radius, avg_error * 100)
            
            -- ================================================
            -- 方向判断（关键新增部分）
            -- ================================================
            
            -- 计算轨迹上的角度序列
            local angles = {}
            for _, p in ipairs(trajectory_points) do
                local angle = calculate_angle(fitted_circle.center, p)
                table.insert(angles, angle)
            end
            
            -- 检测旋转方向
            local rotation_direction = detect_rotation_direction(angles)
            local direction_match = is_direction_ok(rotation_direction)
            
            -- 计算角度覆盖范围
            local angle_span = check_angle_coverage(trajectory_points, fitted_circle)
            
            status_msg = status_msg .. string.format(", 方向: %s", get_direction_name(rotation_direction))
            
            -- 判断是否为圆形轨迹（考虑方向要求）
            local is_circle = false
            if avg_error <= max_fit_error then
                if required_direction == 'both' then
                    is_circle = true  -- 不限制方向，圆形就算
                elseif direction_match then
                    is_circle = true  -- 方向符合要求
                elseif rotation_direction ~= 'unknown' then
                    -- 方向不符，提示错误方向
                    status_msg = status_msg .. string.format(" ✗方向错误(需要%s)", get_direction_name(required_direction))
                end
            end
            
            if is_circle then
                circle_detection_count = circle_detection_count + 1
                status_msg = status_msg .. " ✓圆形轨迹"
                
                if circle_detection_count >= required_circle_count and not success_triggered and angle_span >= min_angle_span then
                    success_triggered = true
                    local dir_text = (required_direction ~= 'both') and (get_direction_name(required_direction) .. " ") or ""
                    return 0, string.format('%s圆形运动检测成功! %s', dir_text, status_msg)
                end
            else
                if avg_error <= max_fit_error and not direction_match then
                    -- 圆形但方向不对，不增加计数但也不清零
                else
                    if circle_detection_count > 0 then
                        circle_detection_count = 0
                    end
                end
                if avg_error > max_fit_error then
                    status_msg = status_msg .. " ✗非圆形"
                end
            end
        else
            status_msg = "Cannot fit circle"
            circle_detection_count = 0
        end
    else
        status_msg = string.format("Collecting points: %d/%d", #trajectory_points, min_points_for_fit)
    end
    
    if success_triggered then
        return 0, 'Already completed'
    elseif circle_detection_count > 0 then
        return 3, string.format('圆形: %d/%d | %s', 
               circle_detection_count, required_circle_count, status_msg)
    else
        return 1, status_msg
    end
end

-- ============================================================
-- 生命周期函数
-- ============================================================

function RunScript_ff264eb1_4816_4077_b7ac_107f63603ae1.cleanup(this, ctx)
    clear_trajectory()
    prev_center = nil
    success_triggered = false
end

function RunScript_ff264eb1_4816_4077_b7ac_107f63603ae1.on_process_begin(this, ctx)
    clear_trajectory()
    prev_center = nil
    success_triggered = false
end

function RunScript_ff264eb1_4816_4077_b7ac_107f63603ae1.on_process_end(this, ctx)
    clear_trajectory()
    prev_center = nil
    success_triggered = false
end

function RunScript_ff264eb1_4816_4077_b7ac_107f63603ae1.get_trajectory_points()
    return trajectory_points
end

function RunScript_ff264eb1_4816_4077_b7ac_107f63603ae1.get_statistics()
    return {
        point_count = #trajectory_points,
        circle_detection_count = circle_detection_count,
        required = required_circle_count,
        success = success_triggered
    }
end