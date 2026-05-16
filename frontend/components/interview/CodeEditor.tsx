"use client";

import { useRef } from "react";
import Editor, { type OnMount } from "@monaco-editor/react";
import type { Language } from "@/lib/piston";
import { MONACO_LANGUAGE_MAP } from "@/lib/piston";

interface CodeEditorProps {
  code: string;
  language: Language;
  onChange: (value: string) => void;
}

export default function CodeEditor({ code, language, onChange }: CodeEditorProps) {
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);

  const handleMount: OnMount = (editor) => {
    editorRef.current = editor;
    editor.focus();
  };

  return (
    <div className="h-full w-full overflow-hidden rounded-xl" style={{ border: "1px solid rgba(255,255,255,0.08)" }}>
      <Editor
        height="100%"
        language={MONACO_LANGUAGE_MAP[language]}
        value={code}
        theme="vs-dark"
        onMount={handleMount}
        onChange={(v) => onChange(v ?? "")}
        options={{
          fontSize: 14,
          fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, monospace",
          fontLigatures: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          lineNumbers: "on",
          renderLineHighlight: "gutter",
          padding: { top: 16, bottom: 16 },
          tabSize: 4,
          insertSpaces: true,
          wordWrap: "on",
          bracketPairColorization: { enabled: true },
          suggest: { showSnippets: true },
          quickSuggestions: true,
          parameterHints: { enabled: true },
          scrollbar: {
            verticalScrollbarSize: 6,
            horizontalScrollbarSize: 6,
          },
        }}
      />
    </div>
  );
}
