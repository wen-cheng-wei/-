"""
批量生成工序配置文件脚本（增强版 + 保存/加载配置）
- 支持加载已保存配置跳过重复输入
- 支持保存当前配置以备复用
- 保留 Lua 模式、额外工具自动注入、RunScript 置末等功能
"""

import json
import uuid
import os
import re
from typing import List, Dict, Any

DEFAULT_TOOLS_CONFIG = "tools_config.json"
SAVED_CONFIGS_FILE = "saved_configs.json"

DEFAULT_PROCESS_ATTRS = {
    "description": "",
    "limit_time": 0,
    "logo": "\n"
}

DEFAULT_TOP_LEVEL = {
    "cameras": None,
    "devices": None,
    "vars": None,
    "description": ""
}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_ns_for_runscript() -> str:
    return f"RunScript_{uuid.uuid4().hex}"


def load_tool_templates(config_path: str = DEFAULT_TOOLS_CONFIG) -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(config_path):
        default_tools = {
            "1": {"class_id": "ImageCapture", "args": {"affect_image": True, "enabled": True, "name": ""}},
            "2": {
                "class_id": "DLObjDetect",
                "args": {
                    "enabled": True, "model_path": "", "name": "", "nms_threshold": 0.44999998807907104,
                    "roi": None, "threshold": 0.25, "valid": False
                }
            },
            "3": {"class_id": "RunScript", "args": {"enabled": True, "name": "", "ns": "", "script": ""}}
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_tools, f, indent='\t', ensure_ascii=False)
        print(f"已创建默认工具配置文件：{config_path}")
        return default_tools
    else:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        tool_templates = {}
        for key, tool in data.items():
            if key == "extra_tools":
                continue
            if "class_id" not in tool or "args" not in tool:
                raise ValueError(f"工具配置项 {key} 缺少 class_id 或 args 字段")
            tool_templates[key] = tool
        return tool_templates


def replace_namespace(script_content: str, new_ns: str) -> str:
    if not script_content:
        return script_content
    pattern = r'RunScript_[a-f0-9_]+'
    updated = re.sub(pattern, new_ns, script_content)
    if 'RunScript_' in updated:
        updated = re.sub(r'RunScript_[a-f0-9_]+', new_ns, updated)
    return updated


def build_tool(tool_template: Dict[str, Any], process_index: int, tool_type_key: str, script_content: str = "") -> Dict[str, Any]:
    class_id = tool_template["class_id"]
    tool_name = f"{class_id}{process_index}"

    args_copy = json.loads(json.dumps(tool_template["args"]))
    args_copy["name"] = tool_name

    if class_id == "RunScript" and "ns" in args_copy:
        new_ns = generate_ns_for_runscript()
        args_copy["ns"] = new_ns
        if script_content:
            updated_script = replace_namespace(script_content, new_ns)
            args_copy["script"] = updated_script

    return {
        "args": args_copy,
        "class_id": class_id,
        "id": generate_uuid(),
        "name": tool_name
    }


def load_lua_files(folder_path: str) -> List[Dict[str, str]]:
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Lua 文件夹不存在：{folder_path}")
    lua_files = []
    for file in os.listdir(folder_path):
        if file.endswith('.lua'):
            match = re.match(r'(\d+)-(.+?)\.lua$', file)
            if match:
                seq = int(match.group(1))
                job_name = match.group(2)
                lua_files.append({
                    "seq": seq,
                    "job_name": job_name,
                    "filename": file,
                    "path": os.path.join(folder_path, file)
                })
    lua_files.sort(key=lambda x: x["seq"])
    for i, item in enumerate(lua_files, 1):
        item["new_seq"] = i
        with open(item["path"], 'r', encoding='utf-8') as f:
            item["content"] = f.read()
    return lua_files


def resolve_output_path(user_input: str, lua_folder: str = None) -> str:
    if not user_input:
        user_input = "output.json"
    if not user_input.endswith('.json'):
        user_input += '.json'
    if os.path.sep in user_input or '/' in user_input:
        return user_input
    else:
        if lua_folder:
            return os.path.join(lua_folder, user_input)
        else:
            return user_input


# ---------- 保存/加载配置 ----------
def load_all_saved_configs() -> Dict[str, dict]:
    if not os.path.exists(SAVED_CONFIGS_FILE):
        return {}
    try:
        with open(SAVED_CONFIGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取保存的配置文件出错: {e}，将忽略历史配置")
        return {}


def save_config_to_file(name: str, config_data: dict):
    all_configs = load_all_saved_configs()
    if name in all_configs:
        print(f"错误：保存名称 '{name}' 已存在，请使用其他名称。")
        return False
    all_configs[name] = config_data
    try:
        with open(SAVED_CONFIGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_configs, f, indent='\t', ensure_ascii=False)
        print(f"配置已保存为：{name}")
        return True
    except Exception as e:
        print(f"保存失败：{e}")
        return False


def select_saved_config(saved_configs: Dict[str, dict]) -> dict:
    names = list(saved_configs.keys())
    if len(names) == 1:
        print(f"自动使用唯一保存配置：{names[0]}")
        return saved_configs[names[0]]
    print("已保存的配置列表：")
    for idx, name in enumerate(names, 1):
        print(f"  {idx}. {name}")
    while True:
        choice = input("请输入配置序号（或输入名称）: ").strip()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(names):
                return saved_configs[names[idx - 1]]
        elif choice in saved_configs:
            return saved_configs[choice]
        print("无效选择，请重新输入")


def apply_saved_config(config_data: dict):
    """从保存的配置数据中提取参数并直接生成输出"""
    tools_config_path = config_data.get("tools_config_path", DEFAULT_TOOLS_CONFIG)
    if not os.path.exists(tools_config_path):
        raise FileNotFoundError(f"工具配置文件 {tools_config_path} 不存在，无法使用保存配置")

    tool_templates = load_tool_templates(tools_config_path)
    selected_keys = config_data["selected_keys"]
    mode = config_data["mode"]
    lua_folder = config_data.get("lua_folder")
    process_count = config_data.get("process_count")
    top_name = config_data["top_name"]
    top_code = config_data["top_code"]
    output_file = config_data.get("output_file", "")

    # 提取额外工具
    extra_tools = []
    try:
        with open(tools_config_path, 'r', encoding='utf-8') as f:
            full_config = json.load(f)
        extra_tools = full_config.get("extra_tools", [])
    except Exception:
        pass

    # 验证工具存在
    for key in selected_keys:
        if key not in tool_templates:
            raise ValueError(f"工具编号 {key} 不存在于当前工具配置文件")

    selected_tools = [(key, tool_templates[key]) for key in selected_keys]
    has_runscript = any(t[1]["class_id"] == "RunScript" for t in selected_tools)

    lua_list = []
    if mode == "2":
        if not lua_folder:
            raise ValueError("Lua 模式下缺少 lua_folder")
        lua_list = load_lua_files(lua_folder)
        process_count = len(lua_list)
    else:
        if not process_count or process_count <= 0:
            raise ValueError("空白模式下工序数量无效")

    # 生成工序
    processes = []
    for i in range(1, process_count + 1):
        script_content = ""
        process_name = str(i)

        if mode == "2" and lua_list and has_runscript:
            lua_item = lua_list[i - 1]
            script_content = lua_item["content"]
            process_name = f"{lua_item['new_seq']}-{lua_item['job_name']}"

        non_runscript_tools = []
        runscript_tool = None
        for key, template in selected_tools:
            if template["class_id"] == "RunScript":
                runscript_tool = (key, template)
            else:
                non_runscript_tools.append((key, template))

        tools = [build_tool(template, i, key, script_content) for key, template in non_runscript_tools]

        if i == 1 and extra_tools:
            extra_class_counter = {}
            for extra_template in extra_tools:
                class_id = extra_template["class_id"]
                extra_class_counter[class_id] = extra_class_counter.get(class_id, 0) + 1
                extra_idx = extra_class_counter[class_id]
                tools.append(build_tool(extra_template, extra_idx, "extra", ""))

        if runscript_tool:
            key, run_template = runscript_tool
            tools.append(build_tool(run_template, i, key, script_content))

        proc = {
            "name": process_name,
            **DEFAULT_PROCESS_ATTRS,
            "tools": tools
        }
        processes.append(proc)

    config = {
        "name": top_name,
        "code": top_code,
        **DEFAULT_TOP_LEVEL,
        "processes": processes
    }

    final_output = resolve_output_path(output_file, lua_folder) if output_file else "output.json"
    with open(final_output, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent='\t', ensure_ascii=False)
        f.write('\n')
    print(f"成功生成配置文件：{final_output}")


def main():
    print("=== 批量生成工序配置文件（增强版） ===\n")

    # 先尝试加载已保存配置
    saved_configs = load_all_saved_configs()
    if saved_configs:
        use_saved = input("是否使用已保存的配置？(y/N): ").strip().lower()
        if use_saved == 'y':
            try:
                selected = select_saved_config(saved_configs)
                apply_saved_config(selected)
                return  # 直接结束
            except Exception as e:
                print(f"应用保存配置失败：{e}")
                print("将手动输入参数...\n")
                # 如果失败，继续手动流程

    # ---------- 正常交互流程 ----------
    tools_config_path = input(f"请输入工具配置文件路径（默认 {DEFAULT_TOOLS_CONFIG}）: ").strip() or DEFAULT_TOOLS_CONFIG
    try:
        tool_templates = load_tool_templates(tools_config_path)
    except Exception as e:
        print(f"加载工具配置文件失败：{e}")
        return

    # 额外工具加载
    extra_tools = []
    try:
        with open(tools_config_path, 'r', encoding='utf-8') as f:
            full_config = json.load(f)
        extra_tools = full_config.get("extra_tools", [])
        if extra_tools:
            print(f"检测到 {len(extra_tools)} 个附加工具，将自动添加到第一个工序。")
    except Exception as e:
        print(f"读取额外工具配置时出错：{e}，将忽略额外工具。")

    sorted_keys = sorted(tool_templates.keys(), key=lambda x: int(x) if x.isdigit() else x)
    print("\n可用工具列表：")
    for key in sorted_keys:
        print(f"  {key}. {tool_templates[key]['class_id']}")

    tool_input = input("\n请输入要使用的工具编号（用英文逗号分隔）: ").strip()
    if not tool_input:
        print("错误：至少选择一个工具")
        return
    selected_keys = [k.strip() for k in tool_input.split(',') if k.strip()]
    selected_tools = []
    for key in selected_keys:
        if key not in tool_templates:
            print(f"错误：编号 {key} 不存在")
            return
        selected_tools.append((key, tool_templates[key]))

    has_runscript = any(t[1]["class_id"] == "RunScript" for t in selected_tools)

    print("\n请选择生成模式：")
    print("  1. 空白模式（手动输入工序数量，script 为空）")
    print("  2. Lua 模式（根据 Lua 文件夹自动生成工序并注入 script）")
    mode = input("请输入模式编号 (1/2): ").strip()

    lua_folder = None
    process_count = 0
    lua_list = []

    if mode == "2":
        lua_folder = input("\n请输入 Lua 文件夹路径: ").strip()
        try:
            lua_list = load_lua_files(lua_folder)
            if not lua_list:
                print("错误：文件夹中未找到符合格式的 Lua 文件")
                return
            process_count = len(lua_list)
            print(f"检测到 {process_count} 个 Lua 文件，将生成对应数量的工序。")
        except Exception as e:
            print(f"Lua 文件读取失败：{e}")
            return
    else:
        try:
            process_count = int(input("\n请输入工序数量 N: ").strip())
            if process_count <= 0:
                print("错误：工序数量必须为正整数")
                return
        except ValueError:
            print("错误：工序数量必须为整数")
            return
        lua_list = []

    top_name = input("\n请输入顶层 name（工序集名称）: ").strip()
    if not top_name:
        print("错误：name 不能为空")
        return
    top_code = input("请输入顶层 code（工序编码）: ").strip()
    if not top_code:
        print("错误：code 不能为空")
        return

    if mode == "2":
        output_prompt = "请输入输出 JSON 文件名（默认 output.json，将保存在 Lua 文件夹下）: "
    else:
        output_prompt = "请输入输出 JSON 文件名（默认 output.json）: "
    user_output = input(output_prompt).strip()
    output_file = resolve_output_path(user_output, lua_folder)

    print(f"\n输出文件路径：{output_file}")
    print("正在生成配置...")

    # 生成工序
    processes = []
    for i in range(1, process_count + 1):
        script_content = ""
        process_name = str(i)

        if mode == "2" and lua_list and has_runscript:
            lua_item = lua_list[i - 1]
            script_content = lua_item["content"]
            process_name = f"{lua_item['new_seq']}-{lua_item['job_name']}"

        non_runscript_tools = []
        runscript_tool = None
        for key, template in selected_tools:
            if template["class_id"] == "RunScript":
                runscript_tool = (key, template)
            else:
                non_runscript_tools.append((key, template))

        tools = [build_tool(template, i, key, script_content) for key, template in non_runscript_tools]

        if i == 1 and extra_tools:
            extra_class_counter = {}
            for extra_template in extra_tools:
                class_id = extra_template["class_id"]
                extra_class_counter[class_id] = extra_class_counter.get(class_id, 0) + 1
                extra_idx = extra_class_counter[class_id]
                tools.append(build_tool(extra_template, extra_idx, "extra", ""))

        if runscript_tool:
            key, run_template = runscript_tool
            tools.append(build_tool(run_template, i, key, script_content))

        proc = {
            "name": process_name,
            **DEFAULT_PROCESS_ATTRS,
            "tools": tools
        }
        processes.append(proc)

    config = {
        "name": top_name,
        "code": top_code,
        **DEFAULT_TOP_LEVEL,
        "processes": processes
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent='\t', ensure_ascii=False)
        f.write('\n')
    print(f"成功生成配置文件：{output_file}")

    # ---------- 保存当前配置 ----------
    save_choice = input("\n是否保存当前配置？(y/N): ").strip().lower()
    if save_choice == 'y':
        config_name = input("请输入配置名称（唯一）: ").strip()
        if not config_name:
            print("名称不能为空，放弃保存。")
            return
        # 收集参数
        current_params = {
            "tools_config_path": tools_config_path,
            "selected_keys": selected_keys,
            "mode": mode,
            "top_name": top_name,
            "top_code": top_code,
            "output_file": user_output  # 保存用户输出的文件名
        }
        if mode == "2":
            current_params["lua_folder"] = lua_folder
        else:
            current_params["process_count"] = process_count

        save_config_to_file(config_name, current_params)


if __name__ == "__main__":
    main()


