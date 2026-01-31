#!/usr/bin/env python3
"""
检查Python文件的导入错误
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Set, Dict, Tuple


class ImportChecker:
    def __init__(self, app_dir: str = "app"):
        self.app_dir = Path(app_dir)
        self.errors: List[Tuple[str, str, int]] = []
        
    def check_file(self, file_path: Path) -> List[Tuple[str, str, int]]:
        """检查单个文件的导入错误"""
        file_errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 解析AST
            tree = ast.parse(content)
            
            # 收集所有导入的类型和文件中定义的类型
            imported_types = self._collect_imported_types(tree)
            defined_types = self._collect_defined_types(tree)
            
            # 合并导入和定义的类型
            available_types = imported_types | defined_types
            
            # 检查类型注解中的类型
            for node in ast.walk(tree):
                if isinstance(node, ast.AnnAssign) and node.annotation:
                    self._check_annotation(node.annotation, available_types, file_path, file_errors)
                elif isinstance(node, ast.FunctionDef):
                    # 检查函数参数的类型注解
                    for arg in node.args.args:
                        if arg.annotation:
                            self._check_annotation(arg.annotation, available_types, file_path, file_errors)
                    # 检查返回类型注解
                    if node.returns:
                        self._check_annotation(node.returns, available_types, file_path, file_errors)
                elif isinstance(node, ast.AsyncFunctionDef):
                    # 检查异步函数参数的类型注解
                    for arg in node.args.args:
                        if arg.annotation:
                            self._check_annotation(arg.annotation, available_types, file_path, file_errors)
                    # 检查返回类型注解
                    if node.returns:
                        self._check_annotation(node.returns, available_types, file_path, file_errors)
                        
        except SyntaxError as e:
            file_errors.append((str(file_path), f"Syntax error: {e}", e.lineno))
        except Exception as e:
            file_errors.append((str(file_path), f"Error parsing file: {e}", 0))
            
        return file_errors
    
    def _collect_imported_types(self, tree: ast.AST) -> Set[str]:
        """收集所有导入的类型"""
        imported_types = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_types.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # 处理 from module import name 的情况
                    for alias in node.names:
                        if alias.name == '*':
                            # 通配符导入，我们无法确定具体导入了什么
                            continue
                        imported_types.add(alias.name)
        
        return imported_types
    
    def _collect_defined_types(self, tree: ast.AST) -> Set[str]:
        """收集文件中定义的类型（类名）"""
        defined_types = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                defined_types.add(node.name)
        
        return defined_types
    
    def _check_annotation(self, annotation, available_types: Set[str], file_path: Path, file_errors: List[Tuple[str, str, int]]):
        """检查类型注解中的类型是否已导入"""
        annotation_str = ast.unparse(annotation)
        
        # 提取类型名称（处理复杂类型如 tuple[Tenant, User]）
        type_names = self._extract_type_names(annotation_str)
        
        for type_name in type_names:
            if type_name and not self._is_builtin_type(type_name):
                # 检查是否在可用的类型中
                if type_name not in available_types:
                    file_errors.append((str(file_path), f"Type '{type_name}' used but not imported", 0))
    
    def _extract_type_names(self, annotation_str: str) -> List[str]:
        """从类型注解字符串中提取类型名称"""
        import re
        
        # 处理 tuple[Tenant, User] 这样的类型
        type_names = []
        
        # 匹配基本类型名称（大写开头的标识符）
        basic_types = re.findall(r'\b[A-Z][a-zA-Z0-9_]*\b', annotation_str)
        for type_name in basic_types:
            if not self._is_builtin_type(type_name):
                type_names.append(type_name)
        
        return type_names
    
    def _is_builtin_type(self, type_name: str) -> bool:
        """检查是否为内置类型"""
        builtin_types = {
            'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
            'Optional', 'Union', 'Any', 'None', 'True', 'False', 'Callable',
            'AsyncGenerator', 'AsyncSession', 'Session', 'Request', 'Response',
            'BackgroundTasks', 'Query', 'Depends', 'HTTPException', 'status',
            'BaseModel', 'Field', 'Config', 'from_attributes', 'Exception',
            'Redis', 'RetryConfig', 'ClientTimeout', 'ClientResponse', 'ClientSession'
        }
        return type_name in builtin_types
    
    def check_all_files(self) -> List[Tuple[str, str, int]]:
        """检查所有Python文件"""
        all_errors = []
        
        for py_file in self.app_dir.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                file_errors = self.check_file(py_file)
                all_errors.extend(file_errors)
        
        return all_errors


def main():
    checker = ImportChecker()
    errors = checker.check_all_files()
    
    if errors:
        print("❌ 发现导入错误:")
        for file_path, error_msg, line_no in errors:
            print(f"  {file_path}:{line_no} - {error_msg}")
        sys.exit(1)
    else:
        print("✅ 所有导入检查通过")


if __name__ == "__main__":
    main()
