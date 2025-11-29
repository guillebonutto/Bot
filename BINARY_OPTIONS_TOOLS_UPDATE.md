# Instrucciones para Actualizar BinaryOptionsTools

## 📋 Requisitos Previos

Para compilar e instalar BinaryOptionsToolsV2, necesitas:

### 1. Rust
Descarga e instala desde: https://rustup.rs/

```powershell
# Verifica que Rust está instalado
rustc --version
cargo --version
```

### 2. Visual Studio Build Tools
Descarga desde: https://visualstudio.microsoft.com/downloads/

Instala con estas opciones:
- ☑️ Desktop development with C++
- ☑️ Windows SDK
- ☑️ CMake tools for Windows

### 3. Git (opcional, para actualizaciones)
```powershell
git --version
```

## 🚀 Pasos para Actualizar

### Opción 1: Automático (Recomendado)

```powershell
cd c:\Users\nico\Downloads\PocketOptions\Bot
python update_binary_options_tools.py
```

### Opción 2: Manual

```powershell
cd c:\Users\nico\Downloads\PocketOptions\Bot\BinaryOptionsTools-v2\BinaryOptionsToolsV2

# Actualizar desde git (si aplica)
git pull

# Compilar e instalar
pip install -e .

# Esto tardará 5-15 minutos
```

### Opción 3: Instalar desde ruedas precompiladas (si existen)

Si encuentras archivos `.whl` en `wheels/`:

```powershell
pip install wheels/BinaryOptionsToolsV2-*.whl
```

## ✅ Verificar Instalación

```powershell
python -c "from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync; print('OK')"
```

Si funciona, verás: `OK`

Si falla, el bot usará automáticamente el mock.

## ⚠️ Solución de Problemas

### Error: "linker `link.exe` not found"

```powershell
# Instala Visual Studio Build Tools con C++ support
# https://visualstudio.microsoft.com/downloads/
```

### Error: "cargo not found"

```powershell
# Instala Rust
https://rustup.rs/
```

### Error: "maturin failed"

```powershell
# Intenta actualizar maturin
pip install --upgrade maturin
```

## 📝 Notas

- La compilación toma 5-15 minutos la primera vez
- Puedes seguir usando el bot con mock mientras tanto
- El bot automáticamente usará BinaryOptionsToolsV2 si está disponible

---

**Para cambios rápidos**, simplemente reinicia el bot:

```powershell
python main.py
```

El bot detectará y usará automáticamente BinaryOptionsToolsV2 si está instalado.

