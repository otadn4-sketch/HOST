import React, { useEffect, useRef, useState } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  Search,
  Database,
  Trash2,
  Download,
  Copy,
  Check,
} from 'lucide-react';
import { FileItem, User, Department } from '../types';
import { DataApi } from '../services/api';
import { MarkdownView } from './MarkdownView';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  citedFiles?: string[];
}

interface AiFileChatViewProps {
  files: FileItem[];
  currentUser: User;
  departments: Department[];
}

export const AiFileChatView: React.FC<AiFileChatViewProps> = ({
  files,
  currentUser,
  departments,
}) => {
  const [selectedFileIds, setSelectedFileIds] = useState<string[]>(files.map((f) => f.id));
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome-1',
      role: 'assistant',
      content: `سلام **${currentUser.fullName}**.\n\nاین بخش «گفت‌وگو با منابع» است. پرسش خود را بر اساس اسناد مجاز خود مطرح کنید؛ پاسخ طبق پرامپت سازمانی سامانه تولید می‌شود.`,
      timestamp: 'هم‌اکنون',
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [searchFileQuery, setSearchFileQuery] = useState('');
  const [selectedDeptFilter, setSelectedDeptFilter] = useState('all');
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    setSelectedFileIds(files.map((f) => f.id));
  }, [files]);

  const filteredFileList = files.filter((f) => {
    if (selectedDeptFilter !== 'all' && f.departmentId !== selectedDeptFilter) return false;
    if (searchFileQuery.trim()) {
      const q = searchFileQuery.toLowerCase();
      return f.title.toLowerCase().includes(q) || f.topic.toLowerCase().includes(q);
    }
    return true;
  });

  const handleSendMessage = async (customPrompt?: string) => {
    const textToSend = customPrompt || inputMessage;
    if (!textToSend.trim() || isLoading) return;
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setIsLoading(true);
    try {
      const history = messages.filter((m) => m.id !== 'welcome-1').map((m) => ({ role: m.role, content: m.content }));
      const data = await DataApi.aiChat({
        message: textToSend.trim(),
        file_ids: selectedFileIds,
        history,
      });
      const citedTitles = files.filter((f) => data.response.includes(f.title)).map((f) => f.title);
      setMessages((prev) => [
        ...prev,
        {
          id: `bot-${Date.now()}`,
          role: 'assistant',
          content: data.response,
          timestamp: new Date().toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }),
          citedFiles: citedTitles.length ? citedTitles : undefined,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `bot-err-${Date.now()}`,
          role: 'assistant',
          content: 'در دریافت پاسخ خطایی رخ داد. لطفاً دوباره تلاش کنید.',
          timestamp: new Date().toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const promptSuggestions = [
    { title: 'جمع‌بندی منابع انتخابی', prompt: 'مهم‌ترین نکات منابع انتخاب‌شده را به‌صورت ساختاریافته بیان کن.' },
    { title: 'اقدامات پیشنهادی', prompt: 'بر اساس منابع انتخابی، اقدامات عملی بعدی را فهرست کن.' },
  ];

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-6.5rem)]">
      <div className="w-full lg:w-80 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col shrink-0 overflow-hidden">
        <div className="p-4 border-b border-slate-100 bg-slate-50/70">
          <h2 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
            <Database className="w-4 h-4 text-blue-600" />
            منابع مجاز ({files.length})
          </h2>
          <div className="flex justify-between text-[11px] text-slate-500 pt-2">
            <button onClick={() => setSelectedFileIds(files.map((f) => f.id))} className="text-blue-600 font-bold">انتخاب همه</button>
            <button onClick={() => setSelectedFileIds([])} className="text-slate-500">پاک‌سازی</button>
          </div>
        </div>
        <div className="p-3 border-b border-slate-100 space-y-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute right-2.5 top-2.5 text-slate-400" />
            <input
              value={searchFileQuery}
              onChange={(e) => setSearchFileQuery(e.target.value)}
              placeholder="جستجو در منابع..."
              className="w-full text-xs pr-8 pl-3 py-1.5 bg-slate-100 border border-slate-200 rounded-lg"
            />
          </div>
          <select
            value={selectedDeptFilter}
            onChange={(e) => setSelectedDeptFilter(e.target.value)}
            className="w-full text-xs p-1.5 bg-slate-100 border border-slate-200 rounded-lg"
          >
            <option value="all">همه واحدها</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {filteredFileList.map((file) => {
            const isSelected = selectedFileIds.includes(file.id);
            return (
              <button
                key={file.id}
                onClick={() =>
                  setSelectedFileIds((prev) => (prev.includes(file.id) ? prev.filter((id) => id !== file.id) : [...prev, file.id]))
                }
                className={`w-full text-right p-2.5 rounded-xl border text-xs ${isSelected ? 'bg-blue-50 border-blue-200' : 'bg-white border-slate-200'}`}
              >
                <p className="font-semibold line-clamp-2">{file.title}</p>
                <p className="text-[10px] text-slate-400 mt-1">{file.departmentName}</p>
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                گفت‌وگو با منابع
                <span className="text-[10px] bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <Sparkles className="w-3 h-3" /> طبق پرامپت سازمانی
                </span>
              </h1>
              <p className="text-[11px] text-slate-400">پاسخ فقط بر اساس منابعی که اجازه مشاهده آن‌ها را دارید</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => {
                const text = messages.map((m) => `${m.role}: ${m.content}`).join('\n\n');
                const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'eytan-ai-chat.txt';
                a.click();
                URL.revokeObjectURL(url);
              }}
              className="p-2 text-slate-500 hover:bg-slate-100 rounded-lg"
            >
              <Download className="w-4 h-4" />
            </button>
            <button
              onClick={() => setMessages([{ id: 'welcome-reset', role: 'assistant', content: 'تاریخچه پاک شد. پرسش تازه‌ای مطرح کنید.', timestamp: 'هم‌اکنون' }])}
              className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-5 bg-slate-50/50">
          {messages.map((msg) => {
            const isUser = msg.role === 'user';
            return (
              <div key={msg.id} className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-white ${isUser ? 'bg-blue-600' : 'bg-slate-900'}`}>
                  {isUser ? currentUser.fullName[0] : <Bot className="w-4 h-4" />}
                </div>
                <div className={`max-w-[85%] p-4 rounded-2xl text-xs ${isUser ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200'}`}>
                  {isUser ? <p className="whitespace-pre-wrap">{msg.content}</p> : <MarkdownView content={msg.content} />}
                  {!isUser && (
                    <button
                      onClick={() => { navigator.clipboard.writeText(msg.content); setCopiedMessageId(msg.id); }}
                      className="mt-2 text-[11px] text-slate-400 flex items-center gap-1"
                    >
                      {copiedMessageId === msg.id ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                      کپی
                    </button>
                  )}
                </div>
              </div>
            );
          })}
          {isLoading && <p className="text-xs text-slate-500">در حال تحلیل منابع...</p>}
          <div ref={messagesEndRef} />
        </div>

        <div className="px-4 py-2 border-t border-slate-100 flex gap-2 overflow-x-auto">
          {promptSuggestions.map((item) => (
            <button
              key={item.title}
              onClick={() => handleSendMessage(item.prompt)}
              className="text-[11px] bg-slate-100 px-3 py-1 rounded-full border border-slate-200 whitespace-nowrap"
            >
              {item.title}
            </button>
          ))}
        </div>
        <div className="p-4 border-t border-slate-100 flex gap-2">
          <textarea
            rows={2}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            className="flex-1 text-xs p-2 rounded-xl border border-slate-200 bg-slate-50"
            placeholder="پرسش خود را درباره منابع بنویسید..."
          />
          <button
            onClick={() => handleSendMessage()}
            disabled={!inputMessage.trim() || isLoading}
            className="p-3 rounded-xl bg-blue-600 text-white disabled:bg-slate-200"
          >
            <Send className="w-4 h-4 rotate-180" />
          </button>
        </div>
      </div>
    </div>
  );
};
