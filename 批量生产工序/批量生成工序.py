"""
批量生成工序配置文件脚本
"""
import json
import uuid
import os
import re
from typing import List, Dict, Any

# 默认工具配置文件路径
DEFAULT_TOOLS_CONFIG = "tools_config.json"

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
    """生成 UUID v4 字符串"""
    return str(uuid.uuid4())


def generate_ns_for_runscript() -> str:
    """为 RunScript 生成唯一的 ns 标识符"""
    return f"RunScript_{uuid.uuid4().hex}"


def load_tool_templates(config_path: str = DEFAULT_TOOLS_CONFIG) -> Dict[str, Dict[str, Any]]:
    """从 JSON 文件加载工具模板（若不存在则创建默认）"""
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
        for key, tool in data.items():
            if "class_id" not in tool or "args" not in tool:
                raise ValueError(f"工具配置项 {key} 缺少 class_id 或 args 字段")
        return data


def replace_namespace(script_content: str, new_ns: str) -> str:
    """增强版命名空间替换 - 彻底清除旧 ns 及其后缀"""
    if not script_content:
        return script_content
    
    # 模式1：匹配 RunScript_ 后面所有十六进制和下划线组合（最完整匹配）
    pattern = r'RunScript_[a-f0-9_]+'
    updated = re.sub(pattern, new_ns, script_content)
    
    # 模式2：兜底替换（防止极端情况）
    if 'RunScript_' in updated:
        updated = re.sub(r'RunScript_[a-f0-9_]+', new_ns, updated)
    
    return updated


def build_tool(tool_template: Dict[str, Any], process_index: int, tool_type_key: str, script_content: str = "") -> Dict[str, Any]:
    """构建单个工具，支持注入 script"""
    class_id = tool_template["class_id"]
    tool_name = f"{class_id}{process_index}"

    args_copy = json.loads(json.dumps(tool_template["args"]))
    args_copy["name"] = tool_name

    if class_id == "RunScript" and "ns" in args_copy:
        new_ns = generate_ns_for_runscript()
        args_copy["ns"] = new_ns
        if script_content:
            # 使用增强替换
            updated_script = replace_namespace(script_content, new_ns)
            args_copy["script"] = updated_script

    return {
        "args": args_copy,
        "class_id": class_id,
        "id": generate_uuid(),
        "name": tool_name
    }


def build_process(process_index: int, tool_templates_with_keys: List[tuple], script_content: str = "") -> Dict[str, Any]:
    """生成单个工序"""
    tools = [build_tool(template, process_index, key, script_content) for key, template in tool_templates_with_keys]
    process_name = str(process_index)  # Lua 模式下后续会覆盖

    return {
        "name": process_name,
        **DEFAULT_PROCESS_ATTRS,
        "tools": tools
    }


def load_lua_files(folder_path: str) -> List[Dict[str, str]]:
    """读取并排序 Lua 文件"""
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
    
    # 按原始序号排序后重新编号
    lua_files.sort(key=lambda x: x["seq"])
    for i, item in enumerate(lua_files, 1):
        item["new_seq"] = i
        with open(item["path"], 'r', encoding='utf-8') as f:
            item["content"] = f.read()
    
    return lua_files


def main():
    print("=== 批量生成工序配置文件（增强版） ===\n")

    # 加载工具模板
    tools_config_path = input(f"请输入工具配置文件路径（默认 {DEFAULT_TOOLS_CONFIG}）: ").strip() or DEFAULT_TOOLS_CONFIG
    try:
        tool_templates = load_tool_templates(tools_config_path)
    except Exception as e:
        print(f"加载工具配置文件失败：{e}")
        return

    # 显示可用工具
    sorted_keys = sorted(tool_templates.keys(), key=lambda x: int(x) if x.isdigit() else x)
    print("\n可用工具列表：")
    for key in sorted_keys:
        print(f"  {key}. {tool_templates[key]['class_id']}")

    # 选择工具
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

    # 模式选择
    print("\n请选择生成模式：")
    print("  1. 空白模式（手动输入工序数量，script 为空）")
    print("  2. Lua 模式（根据 Lua 文件夹自动生成工序并注入 script）")
    mode = input("请输入模式编号 (1/2): ").strip()

    if mode == "2":
        # Lua 模式
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
        # 空白模式
        try:
            process_count = int(input("\n请输入工序数量 N: ").strip())
            if process_count <= 0:
                print("错误：工序数量必须为正整数")
                return
        except ValueError:
            print("错误：工序数量必须为整数")
            return
        lua_list = []

    # 顶层信息
    top_name = input("\n请输入顶层 name（工序集名称）: ").strip()
    if not top_name:
        print("错误：name 不能为空")
        return
    top_code = input("请输入顶层 code（工序编码）: ").strip()
    if not top_code:
        print("错误：code 不能为空")
        return

    # 输出文件
    output_file = input("请输入输出 JSON 文件名（默认 output.json）: ").strip() or "output.json"
    if not output_file.endswith('.json'):
        output_file += '.json'

    print("\n正在生成配置...")

    processes = []
    backup_dir = "backup"
    os.makedirs(backup_dir, exist_ok=True)

    for i in range(1, process_count + 1):
        script_content = ""
        process_name = str(i)

        if mode == "2" and lua_list and has_runscript:
            lua_item = lua_list[i-1]
            script_content = lua_item["content"]
            process_name = f"{lua_item['new_seq']}-{lua_item['job_name']}"

            # 保存备份（使用替换后的内容）
            backup_path = os.path.join(backup_dir, f"{lua_item['new_seq']}-{lua_item['job_name']}_generated.lua")
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(replace_namespace(script_content, "placeholder_for_backup"))  # 备份时不替换具体ns，仅保存原逻辑

        proc = build_process(i, selected_tools, script_content)
        proc["name"] = process_name
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
    if mode == "2":
        print(f"Lua 备份文件已保存至：{backup_dir} 文件夹")


if __name__ == "__main__":
    main()

