import React, { useState, useRef, useEffect } from 'react';
import { Sparkles, ArrowRight, RotateCw, ShieldCheck, HelpCircle } from 'lucide-react';
import { ChatMessage, Finding } from '../../types';

interface ContextualAIProps {
  chatMessages: ChatMessage[];
  isAiTyping: boolean;
  onSendMessage: (text: string) => void;
  activeFinding: Finding | null;
}

export const ContextualAI: React.FC<ContextualAIProps> = ({
  chatMessages,
  isAiTyping,
  onSendMessage,
  activeFinding
}) => {
  const [input, setInput] = useState('');
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isAiTyping]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isAiTyping) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const quickChips = [
    'How to resolve circular dependency cycle?',
    'What dynamic import blind spots exist?',
    'How to safely verify legacy calculator removal?',
    'What test suites would break if we touch this code?'
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fadeIn">
      <div className="p-6 rounded-3xl bg-white border border-red-100 shadow-xl space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#FF2E55] to-red-700 flex items-center justify-center text-white shadow-md">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-black text-slate-900">Contextual AI Code Reviewer</h3>
              <p className="text-xs text-slate-500 font-medium">
                Answers grounded strictly in analyzer evidence without fabricating safety claims.
              </p>
            </div>
          </div>

          {activeFinding && (
            <div className="hidden sm:flex items-center gap-2 bg-red-50 text-[#FF2E55] border border-red-200 px-3 py-1 rounded-xl text-xs font-mono font-bold">
              <span>Context:</span>
              <span className="truncate max-w-[120px]">{activeFinding.file.split('/').pop()}</span>
            </div>
          )}
        </div>

        {/* Chat Thread */}
        <div className="space-y-3 max-h-[400px] overflow-y-auto p-4 rounded-2xl bg-slate-50 border border-slate-200">
          {chatMessages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] p-4 rounded-2xl text-xs leading-relaxed whitespace-pre-line font-medium shadow-sm ${
                  msg.role === 'user'
                    ? 'bg-[#FF2E55] text-white font-bold rounded-tr-none'
                    : 'bg-white text-slate-800 border border-slate-200 rounded-tl-none'
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}

          {isAiTyping && (
            <div className="text-xs font-bold text-[#FF2E55] flex items-center gap-2 p-2">
              <RotateCw className="w-3.5 h-3.5 animate-spin" />
              <span>AI is evaluating static analysis evidence & dependencies...</span>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Quick Suggestion Chips */}
        <div className="space-y-1.5 pt-1">
          <span className="text-[10px] font-black uppercase text-slate-400 flex items-center gap-1">
            <HelpCircle className="w-3 h-3" />
            Suggested prompts:
          </span>
          <div className="flex flex-wrap gap-2">
            {quickChips.map((chip) => (
              <button
                key={chip}
                onClick={() => onSendMessage(chip)}
                disabled={isAiTyping}
                className="px-2.5 py-1 rounded-xl bg-red-50 hover:bg-red-100 text-[#FF2E55] text-[11px] font-bold border border-red-200 transition-all text-left disabled:opacity-50"
              >
                💡 {chip}
              </button>
            ))}
          </div>
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="flex gap-2 pt-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isAiTyping}
            placeholder="Ask AI about cycle refactoring, impact radius, or verification steps..."
            className="flex-1 px-4 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs sm:text-sm font-bold focus:outline-none focus:border-[#FF2E55] transition-colors disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isAiTyping}
            className="px-5 py-2.5 rounded-xl bg-[#FF2E55] hover:bg-red-600 disabled:opacity-50 text-white font-black text-xs uppercase shadow-md flex items-center gap-1.5 transition-all"
          >
            <span>Ask</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </form>

        <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
          <span>Grounded in deterministic Knip, Madge & jscpd findings; never hallucinates safe deletion.</span>
        </div>
      </div>
    </div>
  );
};
