import React, { useState } from 'react';
import { Copy, Check, Info, Lightbulb, ShieldAlert } from 'lucide-react';

interface MarkdownViewerProps {
  content: string;
}

export const MarkdownViewer: React.FC<MarkdownViewerProps> = ({ content }) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Render markdown text lines with formatting
  const renderFormattedText = (rawText: string) => {
    // Replace inline code `code`
    const parts = rawText.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);

    return parts.map((part, i) => {
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code
            key={i}
            className="px-1.5 py-0.5 rounded bg-slate-900/10 text-[#FF2E55] font-mono text-[11px] font-bold"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="font-extrabold text-slate-900">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  };

  // Split into blocks: paragraphs, lists, code blocks, alerts, headers
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBuffer: string[] = [];
  let codeLang = '';
  let blockQuoteBuffer: string[] = [];
  let inBlockQuote = false;
  let quoteType = 'NOTE';

  lines.forEach((line, lineIdx) => {
    // 1. Code Block boundary
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        // End of code block
        const codeText = codeBuffer.join('\n');
        const currentIndex = lineIdx;
        elements.push(
          <div
            key={`code-${lineIdx}`}
            className="my-3 rounded-2xl bg-[#0F0F12] border border-slate-800 overflow-hidden shadow-md text-xs font-mono"
          >
            <div className="flex items-center justify-between px-3 py-1.5 bg-[#18181D] border-b border-slate-800 text-[10px] text-slate-400">
              <span className="uppercase font-bold tracking-wider">{codeLang || 'CODE'}</span>
              <button
                onClick={() => handleCopy(codeText, currentIndex)}
                className="flex items-center gap-1 hover:text-white transition-colors"
              >
                {copiedIndex === currentIndex ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <pre className="p-3.5 text-slate-200 overflow-x-auto leading-relaxed">
              <code>{codeText}</code>
            </pre>
          </div>
        );
        codeBuffer = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
        codeLang = line.trim().slice(3).trim();
      }
      return;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      return;
    }

    // 2. GitHub style alerts: > [!CAUTION], > [!NOTE], > [!TIP]
    if (line.startsWith('>')) {
      inBlockQuote = true;
      const stripped = line.slice(1).trim();
      if (stripped.startsWith('[!CAUTION]') || stripped.startsWith('[!WARNING]')) {
        quoteType = 'CAUTION';
      } else if (stripped.startsWith('[!TIP]')) {
        quoteType = 'TIP';
      } else if (stripped.startsWith('[!NOTE]')) {
        quoteType = 'NOTE';
      } else {
        blockQuoteBuffer.push(stripped);
      }
      return;
    } else if (inBlockQuote) {
      // Flush block quote
      const quoteText = blockQuoteBuffer.join(' ');
      elements.push(
        <div
          key={`quote-${lineIdx}`}
          className={`my-3 p-3.5 rounded-2xl border text-xs leading-relaxed flex items-start gap-2.5 ${quoteType === 'CAUTION'
              ? 'bg-red-50/90 border-red-200 text-red-950 font-medium'
              : quoteType === 'TIP'
                ? 'bg-emerald-50/90 border-emerald-200 text-emerald-950 font-medium'
                : 'bg-blue-50/90 border-blue-200 text-blue-950 font-medium'
            }`}
        >
          {quoteType === 'CAUTION' && <ShieldAlert className="w-4 h-4 text-[#FF2E55] shrink-0 mt-0.5" />}
          {quoteType === 'TIP' && <Lightbulb className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />}
          {quoteType === 'NOTE' && <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />}
          <div>{renderFormattedText(quoteText)}</div>
        </div>
      );
      blockQuoteBuffer = [];
      inBlockQuote = false;
    }

    // 3. Headings: ### or ####
    if (line.startsWith('### ')) {
      elements.push(
        <h4 key={`h3-${lineIdx}`} className="text-sm font-black text-slate-900 mt-4 mb-2 flex items-center gap-1.5">
          {renderFormattedText(line.replace('### ', ''))}
        </h4>
      );
      return;
    }

    if (line.startsWith('#### ')) {
      elements.push(
        <h5 key={`h4-${lineIdx}`} className="text-xs font-black uppercase tracking-wider text-slate-700 mt-3 mb-1">
          {renderFormattedText(line.replace('#### ', ''))}
        </h5>
      );
      return;
    }

    // 4. Bullet lists: - or *
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      const itemText = line.trim().slice(2);
      elements.push(
        <div key={`li-${lineIdx}`} className="flex items-start gap-2 text-xs text-slate-700 my-1 leading-relaxed pl-1">
          <span className="text-[#FF2E55] font-bold mt-1 text-[8px]">●</span>
          <span className="flex-1">{renderFormattedText(itemText)}</span>
        </div>
      );
      return;
    }

    // 5. Numbered lists: 1. 2.
    const numMatch = line.trim().match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      elements.push(
        <div key={`num-${lineIdx}`} className="flex items-start gap-2 text-xs text-slate-700 my-1 leading-relaxed pl-1">
          <span className="w-4 h-4 rounded-full bg-red-50 text-[#FF2E55] text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5 border border-red-200">
            {numMatch[1]}
          </span>
          <span className="flex-1">{renderFormattedText(numMatch[2])}</span>
        </div>
      );
      return;
    }

    // 6. Regular text line or spacing
    if (line.trim() === '') {
      elements.push(<div key={`sp-${lineIdx}`} className="h-1.5" />);
    } else {
      elements.push(
        <p key={`p-${lineIdx}`} className="text-xs text-slate-700 leading-relaxed my-1">
          {renderFormattedText(line)}
        </p>
      );
    }
  });

  // Flush any trailing blockquote
  if (inBlockQuote && blockQuoteBuffer.length > 0) {
    elements.push(
      <div
        key="quote-end"
        className={`my-3 p-3.5 rounded-2xl border text-xs leading-relaxed flex items-start gap-2.5 ${quoteType === 'CAUTION'
            ? 'bg-red-50/90 border-red-200 text-red-950 font-medium'
            : 'bg-blue-50/90 border-blue-200 text-blue-950 font-medium'
          }`}
      >
        <ShieldAlert className="w-4 h-4 text-[#FF2E55] shrink-0 mt-0.5" />
        <div>{renderFormattedText(blockQuoteBuffer.join(' '))}</div>
      </div>
    );
  }

  return <div className="space-y-1 font-sans">{elements}</div>;
};
