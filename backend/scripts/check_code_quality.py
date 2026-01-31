#!/usr/bin/env python3
"""
Comprehensive code quality checker for Python files
"""

import ast
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any


class CodeQualityChecker:
    """Check code quality for Python files"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def check_file(self, file_path: str) -> bool:
        """Check a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check syntax
            tree = ast.parse(content)
            
            # Check for common issues
            self._check_imports(tree, file_path)
            self._check_functions(tree, file_path)
            self._check_classes(tree, file_path)
            self._check_variables(tree, file_path)
            
            return True
            
        except SyntaxError as e:
            self.errors.append(f"❌ Syntax Error in {file_path}: Line {e.lineno} - {e.msg}")
            return False
        except Exception as e:
            self.errors.append(f"❌ Error reading {file_path}: {e}")
            return False
    
    def _check_imports(self, tree: ast.AST, file_path: str):
        """Check import statements"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith('.'):
                        self.warnings.append(f"⚠️  Relative import in {file_path}: {alias.name}")
            
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith('.'):
                    self.warnings.append(f"⚠️  Relative import in {file_path}: from {node.module}")
    
    def _check_functions(self, tree: ast.AST, file_path: str):
        """Check function definitions"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for missing docstrings
                if not ast.get_docstring(node):
                    self.warnings.append(f"⚠️  Function without docstring in {file_path}: {node.name}")
                
                # Check for too many arguments
                if len(node.args.args) > 10:
                    self.warnings.append(f"⚠️  Function with many arguments in {file_path}: {node.name} ({len(node.args.args)} args)")
    
    def _check_classes(self, tree: ast.AST, file_path: str):
        """Check class definitions"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for missing docstrings
                if not ast.get_docstring(node):
                    self.warnings.append(f"⚠️  Class without docstring in {file_path}: {node.name}")
    
    def _check_variables(self, tree: ast.AST, file_path: str):
        """Check variable usage"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                # Check for single letter variable names (except i, j, k in loops)
                if len(node.id) == 1 and node.id not in ['i', 'j', 'k']:
                    # Check if it's in a loop context
                    parent = getattr(node, 'parent', None)
                    if not self._is_in_loop_context(node):
                        self.warnings.append(f"⚠️  Single letter variable in {file_path}: {node.id}")
    
    def _is_in_loop_context(self, node: ast.Name) -> bool:
        """Check if a node is in a loop context"""
        current = node
        while hasattr(current, 'parent'):
            current = current.parent
            if isinstance(current, (ast.For, ast.While)):
                return True
        return False
    
    def check_directory(self, directory: str) -> tuple[int, int]:
        """Check all Python files in a directory"""
        total_files = 0
        error_files = 0
        
        for root, dirs, files in os.walk(directory):
            # Skip virtual environment and cache directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    total_files += 1
                    
                    if not self.check_file(file_path):
                        error_files += 1
        
        return total_files, error_files
    
    def print_report(self):
        """Print the quality report"""
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        print(f"\n📊 Summary:")
        print(f"  Errors: {len(self.errors)}")
        print(f"  Warnings: {len(self.warnings)}")


def main():
    """Main function"""
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = "app"
    
    print(f"🔍 Checking code quality for Python files in: {target}")
    print("=" * 60)
    
    checker = CodeQualityChecker()
    total_files, error_files = checker.check_directory(target)
    
    print("=" * 60)
    print(f"📊 Files Summary:")
    print(f"   Total files checked: {total_files}")
    print(f"   Files with errors: {error_files}")
    print(f"   Files with valid syntax: {total_files - error_files}")
    
    checker.print_report()
    
    if error_files == 0 and len(checker.errors) == 0:
        print("\n✅ All files have valid syntax!")
        return 0
    else:
        print("\n❌ Found issues!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
