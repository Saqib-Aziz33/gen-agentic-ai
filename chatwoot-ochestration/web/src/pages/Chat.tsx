import React, { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Send,
  Bot,
  User as UserIcon,
  Sparkles,
  Command,
  Info,
  BadgeCheck,
  ChevronRight
} from 'lucide-react';
import { customerService } from '../services/customerService';
import { useAuthStore } from '../store/authStore';
import { cn } from '../lib/utils';

interface Message {
  role: 'user' | 'agent';
  content: string;
  time: Date;
  customerInfo?: any;
}

const Chat = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'agent',
      content: "Hello! I'm your AI Customer Agent. I can help you query customer data, extract information from transcripts, or summarize interactions. How can I assist you today?",
      time: new Date()
    }
  ]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user } = useAuthStore();

  const scrollToBottom = () => {
    if (messages.length > 1) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  };

  useEffect(scrollToBottom, [messages]);

  const apiChatMutation = useMutation({
    mutationFn: (message: string) => customerService.chatWithAgent(message),
    onSuccess: (data) => {
      setMessages(prev => [...prev, {
        role: 'agent',
        content: data.response,
        time: new Date(),
        customerInfo: data.customer_provided ? data : null
      }]);
    }
  });

  const handleSend = (e: React.FormEvent | React.KeyboardEvent) => {
    e.preventDefault();
    if (!input.trim() || apiChatMutation.isPending) return;

    const userMessage = input;
    setMessages(prev => [...prev, { role: 'user', content: userMessage, time: new Date() }]);
    setInput('');
    apiChatMutation.mutate(userMessage);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  };

  return (
    <div className="max-w-6xl mx-auto h-[calc(100vh-160px)] flex flex-col font-sans">
      <header className="mb-8 flex justify-between items-center bg-slate-900/40 p-6 rounded-3xl border border-slate-800 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-600/20 ring-4 ring-indigo-600/10">
            <Bot className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              Conversational Intel Agent
              <span className="text-[10px] font-black bg-indigo-600/20 text-indigo-400 px-2 py-0.5 rounded-full border border-indigo-500/20 uppercase tracking-widest">v2.0 Beta</span>
            </h1>
            <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mt-0.5 mt-1">
              Active Session • {user?.username}
            </p>
          </div>
        </div>

        <div className="hidden md:flex gap-6">
          <div className="flex flex-col items-end">
            <span className="text-xs font-bold text-slate-600 uppercase tracking-widest leading-none mb-1">Status</span>
            <span className="text-sm font-bold text-emerald-500 flex items-center">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-2 animate-pulse" />
              Operational
            </span>
          </div>
        </div>
      </header>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto space-y-8 pr-4 mb-6 custom-scrollbar scroll-smooth">
        {messages.map((msg, i) => (
          <div key={i} className={cn(
            "flex gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300",
            msg.role === 'user' ? "flex-row-reverse" : ""
          )}>
            <div className={cn(
              "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-lg",
              msg.role === 'user' ? "bg-slate-800 text-slate-400" : "bg-indigo-600 text-white"
            )}>
              {msg.role === 'user' ? <UserIcon className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
            </div>

            <div className={cn(
              "flex flex-col max-w-[75%]",
              msg.role === 'user' ? "items-end text-right" : "items-start"
            )}>
              <div className={cn(
                "p-5 rounded-2xl text-[15px] font-medium leading-relaxed transition-all",
                msg.role === 'user'
                  ? "bg-slate-800 text-slate-200 rounded-tr-none border border-slate-700/50"
                  : "bg-slate-900 text-slate-200 rounded-tl-none border border-slate-800 shadow-xl shadow-black/10"
              )}>
                <p className="whitespace-pre-wrap">{msg.content}</p>

                {msg.customerInfo && (
                  <div className="mt-4 pt-4 border-t border-white/5 space-y-3">
                    <div className="flex items-center gap-2 text-indigo-400 font-bold text-[10px] uppercase tracking-widest">
                      <Sparkles className="w-3 h-3" />
                      Intelligence Found
                    </div>
                    <div className="bg-indigo-600/10 border border-indigo-500/20 rounded-xl p-3 flex justify-between items-center group cursor-pointer hover:bg-indigo-600/20 transition-all">
                      <span className="text-xs font-semibold text-slate-300">New customer context detected</span>
                      <ChevronRight className="w-3 h-3 text-indigo-500 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                )}
              </div>
              <span className="text-[10px] text-slate-600 font-bold uppercase tracking-widest mt-2 px-1">
                {msg.role === 'agent' ? "System Agent" : user?.username} • {msg.time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        ))}
        {apiChatMutation.isPending && (
          <div className="flex gap-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl rounded-tl-none flex gap-1.5 items-center">
              <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="relative z-10">
        <div className="absolute -top-12 left-6 flex gap-2">
          <div className="bg-slate-900 border border-slate-800 px-3 py-1 rounded-full text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center shadow-lg">
            <Command className="w-3 h-3 mr-1.5" />
            Ask about "customer 123"
          </div>
          <div className="bg-slate-900 border border-slate-800 px-3 py-1 rounded-full text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center shadow-lg">
            <Info className="w-3 h-3 mr-1.5" />
            "Summarize transcript"
          </div>
        </div>

        <form onSubmit={handleSend} className="relative group">
          <textarea
            rows={1}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              // Auto-grow: reset height then set to scrollHeight
              e.target.style.height = 'auto';
              e.target.style.height = `${e.target.scrollHeight}px`;
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type your instruction or query here... (Shift+Enter for new line)"
            className="w-full bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-3xl pl-8 pr-24 py-6 text-white text-lg placeholder-slate-600 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-600/50 shadow-2xl transition-all font-medium resize-none overflow-hidden leading-relaxed"
            style={{ minHeight: '76px', maxHeight: '240px', overflowY: 'auto' }}
          />
          <button
            type="submit"
            disabled={!input.trim() || apiChatMutation.isPending}
            className="absolute right-4 bottom-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 p-4 rounded-2xl text-white shadow-xl shadow-indigo-600/20 disabled:shadow-none transform active:scale-95 transition-all"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
        <p className="text-center text-[10px] text-slate-600 font-bold uppercase tracking-widest mt-4">
          The agent uses LangGraph to contextually resolve customer data from PostgreSQL
        </p>
      </div>
    </div>
  );
};

export default Chat;
