#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para actualizar BinaryOptionsTools desde repositorio
Requiere git y rust (para compilación)
"""

import subprocess
import sys
import os
import shutil

def run_command(cmd, cwd=None):
    """Ejecutar comando y retornar exit code"""
    print(f"  > {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr and result.returncode != 0:
        print(result.stderr)
    return result.returncode

def main():
    print("=" * 70)
    print("ACTUALIZAR BinaryOptionsTools")
    print("=" * 70)
    
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    tools_dir = os.path.join(bot_dir, "BinaryOptionsTools-v2")
    
    if not os.path.exists(tools_dir):
        print(f"\n❌ Directorio no encontrado: {tools_dir}")
        return 1
    
    print(f"\n📂 Directorio: {tools_dir}")
    
    # Paso 1: Git pull
    print("\n1️⃣  Actualizando repositorio con git pull...")
    if run_command(["git", "pull"], cwd=tools_dir) == 0:
        print("   ✅ Repositorio actualizado")
    else:
        print("   ⚠️ Git pull falló (quizás no es un repo git)")
    
    # Paso 2: Verificar compiladores
    print("\n2️⃣  Verificando compiladores necesarios...")
    
    # Verificar Rust
    if run_command(["rustc", "--version"]) == 0:
        print("   ✅ Rust disponible")
    else:
        print("   ❌ Rust no está instalado")
        print("   Descarga desde: https://rustup.rs/")
        return 1
    
    # Verificar compilador C++
    if run_command(["cl.exe"], cwd="C:\\Program Files\\Microsoft Visual Studio\\2022") == 0:
        print("   ✅ Visual Studio C++ disponible")
    else:
        print("   ⚠️ Visual Studio C++ no encontrado")
        print("   Puedes instalar: https://visualstudio.microsoft.com/downloads/")
    
    # Paso 3: Compilar BinaryOptionsToolsV2
    print("\n3️⃣  Compilando BinaryOptionsToolsV2 (esto puede tardar varios minutos)...")
    tools_v2_dir = os.path.join(tools_dir, "BinaryOptionsToolsV2")
    
    if run_command(["pip", "install", "-e", "."], cwd=tools_v2_dir) == 0:
        print("   ✅ BinaryOptionsToolsV2 compilado e instalado")
    else:
        print("   ❌ Error compilando BinaryOptionsToolsV2")
        print("\n   Soluciones:")
        print("   1. Instala Visual Studio con C++ build tools")
        print("   2. Instala Rust desde https://rustup.rs/")
        print("   3. Ejecuta: pip install --upgrade setuptools wheel")
        return 1
    
    print("\n" + "=" * 70)
    print("✅ ACTUALIZACIÓN COMPLETADA")
    print("=" * 70)
    print("\nAhora el bot usará BinaryOptionsToolsV2 compilado localmente.")
    print("\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
