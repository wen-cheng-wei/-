function TableToString(t)
	local parts= {}
	for k,v in pairs(t) do
		local keyStr = type(k) == "string" and string.format('[%q]',k) or tostring(k)
		local valStr = type(v) == "string" and string.format('%q',v) or tostring(v)
		table.insert(parts,keyStr.."="..valStr)
	end
	return "{"..table.concat(parts,",").."}"
end

--获取在对象检测中自定义ROI区域
function ROI(this, ctx)
	local tool = ctx:get_tool_by_name("tool_name")
	local roi = tool:roi()
	for _,obj in ipairs(roi) do
		if obj.type == "rect" then 
			return obj.value.left,obj.value.bottom,obj.value.right,obj.value.top
		end
	end
end

--获取标记点并上传日志
function Upload_Log(this, ctx)
	local tool = ctx:get_tool_by_name("tool_name")
	local points = tool:origin_point_list()
	for _,point in ipairs(points) do
		print('x:'..point.x..',y:'..point.y)
	end
end

--报警灯
function Alarm(this, ctx)
	local tool = ctx:get_tool_by_name("警报控制")
	tool:exec(ctx)
end

--事件触发作业开始，暂停，恢复，停止，发送NG信号
--1、System.send_event(event[, arg])
--  其中的参数event是一个字符串，表示事件的名称，目前可发送的事件有start, pause, resume, stop,NG分别表示开始作业，暂停作业，恢复作业，停止作业，发送NG信号。
--  第二个参数arg是可选的参数，也是个字符串，将会以arg的值传给上位机进行ng展示。arg内可以使用两个占位符：
--  %n：工序名称
--  %t：当前工序耗时
--  当arg内包含有占位符时会自动修改为对应的数据
--  示例：System.send_event("start", "工序1")、System.send_event("pause", "工序1")、System.send_event("resume", "工序1")、System.send_event("stop", "工序1")、System.send_event("NG", "工序1")
--  示例：System.send_event("start", "工序1")、System.send_event("pause", "工序1")、System.send_event("resume", "工序1")、System.send_event("stop", "工序1")、System.send_event("NG", "工序1")

--计算识别框的中心点
function Center(bounding_box)
	local x = (bounding_box.left + bounding_box.right) / 2
	local y = (bounding_box.bottom + bounding_box.top) / 2
	return x,y
end

--通过点乘计算两个向量直接的角度
function Angle(v1,v2) --v1,v2为向量，返回角度，单位为弧度
	local dot = v1.x * v2.x + v1.y * v2.y   --点乘
	local mag1 = math.sqrt(v1.x * v1.x + v1.y * v1.y) --v1的模
	local mag2 = math.sqrt(v2.x * v2.x + v2.y * v2.y) --v2的模
	local angle = math.acos(dot / (mag1 * mag2)) --角度，单位为弧度
	return angle
end


