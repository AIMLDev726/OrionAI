@echo off
echo Installing OrionAI in development mode...

REM Install the package in development mode
pip install -e .

echo.
echo OrionAI CLI installed successfully!
echo.
echo You can now run:
echo   orionai          - Start the interactive CLI
echo   orionai-ui       - Start the Streamlit UI
echo.
echo First time setup:
echo 1. Run 'orionai' to start the CLI
echo 2. Follow the setup wizard to configure your LLM provider
echo 3. Enter your API key (OpenAI, Anthropic, or Google)
echo 4. Create a new session and start chatting!
echo.
echo Session data will be stored in: %USERPROFILE%\.orionai\
echo.
pause
