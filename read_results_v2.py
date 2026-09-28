with open(r'c:\Users\hp\AppData\Roaming\Code\User\workspaceStorage\b06bd39f071f63a36ae2f66d6221a725\GitHub.copilot-chat\chat-session-resources\18baf5d3-336e-40e3-b53f-57de9277c6eb\call_MHxSaFJTUG5vbXhIV1R3QXpIRXg__vscode-1778758440607\content.txt', 'rb') as f:
    content = f.read()
    # Try to decode as utf-16-le but handle errors
    try:
        print(content.decode('utf-16'))
    except:
        print(content.decode('latin1')) # Fallback
