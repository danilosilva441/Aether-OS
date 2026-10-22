@echo off
setlocal

if exist .env (
  for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if not "%%A"=="" set %%A=%%B
  )
)

if "%AETHER_LLM_BACKEND%"=="" set AETHER_LLM_BACKEND=ollama
if "%AETHER_MODEL%"=="" set AETHER_MODEL=qwen2.5:3b
if "%OLLAMA_URL%"=="" set OLLAMA_URL=http://localhost:11434
if "%AETHER_HOST%"=="" set AETHER_HOST=0.0.0.0
if "%AETHER_PORT%"=="" set AETHER_PORT=8000

python -m uvicorn main:app --host %AETHER_HOST% --port %AETHER_PORT%
endlocal
