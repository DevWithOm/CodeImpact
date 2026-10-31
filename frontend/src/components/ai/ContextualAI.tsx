import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  ArrowRight,
  RotateCcw,
  ShieldCheck,
  HelpCircle,
  Cpu,
  User,
  Trash2
} from 'lucide-react';
import { ChatMessage, Finding } from '../../types';
import { MarkdownViewer } from './MarkdownViewer';
import { ContextPanel } from './ContextPanel';

interface ContextualAIProps {
  chatMessages: ChatMessage[];
  isAiTyping: boolean;
  onSendMessage: (text: string) => void;
  activeFinding: Finding | null;
  findings: Finding[];
  onSelectFinding: (finding: Finding) => void;
  onClearChat?: () => void;
  onNavigateToFindings?: () => void;
  onNavigateToGraph?: (finding: Finding) => void;
  repoUrl?: string;
  branch?: string;
}

export const ContextualAI: React.FC<ContextualAIProps> = ({
  chatMessages,
  isAiTyping,
  onSendMessage,
  activeFinding,
  findings,
  onSelectFinding,
  onClearChat,
  onNavigateToFindings = () => {},
  onNavigateToGraph = () => {},
  repoUrl = 'https://github.com/facebook/react',
  branch = 'main'
}) => {
  const [input, setInput] = useState('');
  const chatBottomRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isAiTyping]);

  const handleSend = () => {
    if (!input.trim() || isAiTyping) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestedQuestions = [
    { label: 'Why was this code flagged?', icon: '🔬' },
    { label: 'What could break if I remove this code?', icon: '💥' },
    { label: 'Is it safe to delete?', icon: '⚠️' },
    { label: 'Which modules depend on this file?', icon: '🔗' },
    { label: 'Which tests should I run before changing it?', icon: '🧪' },
    { label: 'Is this finding reliable or a false positive?', icon: '🎯' },
    { label: 'What should I verify before deleting this code?', icon: '📋' },
    { label: 'Explain this finding in simple terms.', icon: '💡' }
  ];

  return (
    <div className="space-y-4 animate-fadeIn">
      {/* 1. Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-6 rounded-3xl bg-white border border-red-100 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-[#FF2E55] to-red-600 flex items-center justify-center text-white shadow-lg shadow-red-500/30">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-black text-slate-900">Contextual AI Assistant</h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-red-50 text-[#FF2E55] border border-red-200">
                Grounded AST Intelligence
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">
              Answers grounded strictly in analyzer evidence, dependency topology, and mapped tests without fabricating safety claims.
            </p>
          </div>
        </div>

        {onClearChat && (
          <button
            onClick={onClearChat}
            className="self-start sm:self-center px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-bold flex items-center gap-1.5 transition-colors"
            title="Reset conversation"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear Chat</span>
          </button>
        )}
      </div>

      {/* 2. Main Workspace: Chat (Left) + Context (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Chat Thread & Input (8 Cols) */}
        <div className="lg:col-span-8 rounded-3xl bg-white border border-slate-200/80 shadow-xl p-5 flex flex-col h-[680px]">
          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-1">
            {chatMessages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center p-6 text-center space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-red-50 text-[#FF2E55] flex items-center justify-center border border-red-100">
                  <Sparkles className="w-6 h-6" />
                </div>
                <h4 className="text-sm font-black text-slate-900">How can I assist your code review?</h4>
                <p className="text-xs text-slate-500 max-w-sm">
                  Select a suggested question below or type your inquiry regarding blast radius, dynamic import blind spots, or safe refactoring steps.
                </p>
              </div>
            )}

            {chatMessages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#FF2E55] to-rose-600 text-white flex items-center justify-center shrink-0 shadow-xs mt-1">
                    <Cpu className="w-4 h-4" />
                  </div>
                )}

                <div className={`max-w-[88%] space-y-1.5 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  {/* Message Bubble */}
                  <div
                    className={`p-4 rounded-2xl text-xs leading-relaxed shadow-xs ${
                      msg.role === 'user'
                        ? 'bg-[#FF2E55] text-white font-bold rounded-tr-none'
                        : 'bg-slate-50 text-slate-800 border border-slate-200/90 rounded-tl-none'
                    }`}
                  >
                    {msg.role === 'assistant' ? (
                      <MarkdownViewer content={msg.text} />
                    ) : (
                      <p className="whitespace-pre-wrap">{msg.text}</p>
                    )}
                  </div>

                  {/* Metadata Footer */}
                  <div className={`flex items-center gap-2 px-1 text-[10px] text-slate-400 font-mono ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {msg.role === 'assistant' && (
                      <span className="font-sans font-bold text-[9px] uppercase px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200">
                        {msg.source === 'backend-gemini' ? 'Gemini 3.8' : 'Grounded Engine'}
                      </span>
                    )}
                    {msg.timestamp && <span>{msg.timestamp}</span>}
                  </div>
                </div>

                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center shrink-0 shadow-xs mt-1">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))}

            {isAiTyping && (
              <div className="flex gap-3 items-center p-3 rounded-2xl bg-red-50/70 border border-red-200/70 text-xs text-[#FF2E55] font-bold animate-pulse">
                <RotateCcw className="w-4 h-4 animate-spin shrink-0" />
                <span>Evaluating static AST evidence, dependency graph & test mapping...</span>
              </div>
            )}

            <div ref={chatBottomRef} />
          </div>

          {/* Suggested Prompts Carousel */}
          <div className="pt-3 border-t border-slate-100 space-y-1.5">
            <span className="text-[10px] font-black uppercase text-slate-400 flex items-center gap-1 font-mono">
              <HelpCircle className="w-3 h-3" />
              Suggested questions for active context:
            </span>

            <div className="flex gap-1.5 overflow-x-auto pb-1 no-scrollbar">
              {suggestedQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => onSendMessage(q.label)}
                  disabled={isAiTyping}
                  className="px-2.5 py-1.5 rounded-xl bg-slate-50 hover:bg-red-50 hover:text-[#FF2E55] hover:border-red-200 text-slate-700 text-[11px] font-bold border border-slate-200/80 transition-all shrink-0 disabled:opacity-50 flex items-center gap-1.5"
                >
                  <span>{q.icon}</span>
                  <span>{q.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Chat Input Form */}
          <div className="pt-2">
            <div className="relative rounded-2xl border border-slate-200 bg-slate-50 focus-within:border-[#FF2E55] focus-within:ring-1 focus-within:ring-[#FF2E55] transition-all">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isAiTyping}
                placeholder={
                  activeFinding
                    ? `Ask anything about ${activeFinding.file.split('/').pop()} (e.g. "What could break if I remove this?")...`
                    : 'Ask about circular cycles, dynamic import blind spots, or refactor safety...'
                }
                rows={2}
                className="w-full px-4 py-2.5 bg-transparent text-xs sm:text-sm font-medium text-slate-800 placeholder-slate-400 focus:outline-none resize-none"
              />

              <div className="flex items-center justify-between px-3 py-1.5 border-t border-slate-200/60 bg-white/70 rounded-b-2xl">
                <span className="text-[10px] text-slate-400 font-mono">
                  Press <strong>Enter</strong> to send, <strong>Shift+Enter</strong> for newline
                </span>

                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isAiTyping}
                  className="px-4 py-1.5 rounded-xl bg-[#FF2E55] hover:bg-red-600 disabled:opacity-40 text-white font-extrabold text-xs shadow-md shadow-red-500/20 flex items-center gap-1.5 transition-all"
                >
                  <span>Send</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="flex items-center gap-2 pt-2 text-[10px] text-slate-400 font-mono">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
              <span>Grounded in AST evidence; strictly refuses to claim unverified safe deletion.</span>
            </div>
          </div>
        </div>

        {/* Available Context Panel (4 Cols) */}
        <div className="lg:col-span-4">
          <ContextPanel
            activeFinding={activeFinding}
            findings={findings}
            onSelectFinding={onSelectFinding}
            onNavigateToFindings={onNavigateToFindings}
            onNavigateToGraph={onNavigateToGraph}
            repoUrl={repoUrl}
            branch={branch}
          />
        </div>
      </div>
    </div>
  );
};