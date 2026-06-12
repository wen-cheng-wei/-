-- DO NOT change this name
RunScript_bb122344_adea_4a61_9d73_f10817857fd2 = {}

local tool_name = 'Blob1'

function RunScript_bb122344_adea_4a61_9d73_f10817857fd2.setup(this, ctx)
	-- TODO: Setting up environment here
end

function TableToString(t)
	local parts= {}
	for k,v in pairs(t) do
		local keyStr = type(k) == "string" and string.format('[%q]',k) or tostring(k)
		local valStr = type(v) == "string" and string.format('%q',v) or tostring(v)
		table.insert(parts,keyStr.."="..valStr)
	end
	return "{"..table.concat(parts,",").."}"
end

function RunScript_bb122344_adea_4a61_9d73_f10817857fd2.exec(this, ctx)
    local tool = ctx:get_tool_by_name(tool_name)
    local result = tool:result()
    LOG.info("x=" .. result.center_mass_x ..",y=" .. result.center_mass_y) 
	return 0, 'Success'
end

function RunScript_bb122344_adea_4a61_9d73_f10817857fd2.cleanup(this, ctx)
	-- TODO: Cleaning up environment here
end

function RunScript_bb122344_adea_4a61_9d73_f10817857fd2.on_process_begin(this, ctx)
	-- TODO: This function will be called before each time the process begin
end

function RunScript_bb122344_adea_4a61_9d73_f10817857fd2.on_process_end(this, ctx)
	-- TODO: This function will be called each time after the process end
end