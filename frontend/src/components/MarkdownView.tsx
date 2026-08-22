import React from 'react';

function inline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}

export const MarkdownView: React.FC<{ content: string; className?: string }> = ({ content, className }) => {
  const lines = (content || '').split('\n');
  const blocks: React.ReactNode[] = [];
  let list: string[] = [];
  const flush = () => {
    if (!list.length) return;
    blocks.push(
      <ul key={`ul-${blocks.length}`} className="list-disc pr-5 space-y-1">
        {list.map((item, i) => (
          <li key={i}>{inline(item)}</li>
        ))}
      </ul>
    );
    list = [];
  };
  lines.forEach((line, idx) => {
    const t = line.trim();
    if (t.startsWith('- ') || t.startsWith('* ')) {
      list.push(t.slice(2));
      return;
    }
    flush();
    if (!t) {
      blocks.push(<div key={`sp-${idx}`} className="h-2" />);
      return;
    }
    if (t.startsWith('### ')) {
      blocks.push(<h4 key={idx} className="font-bold text-sm mt-2">{inline(t.slice(4))}</h4>);
      return;
    }
    if (t.startsWith('## ')) {
      blocks.push(<h3 key={idx} className="font-bold text-sm mt-2">{inline(t.slice(3))}</h3>);
      return;
    }
    if (t.startsWith('# ')) {
      blocks.push(<h2 key={idx} className="font-bold text-base mt-2">{inline(t.slice(2))}</h2>);
      return;
    }
    blocks.push(<p key={idx} className="leading-relaxed">{inline(t)}</p>);
  });
  flush();
  return <div className={className || 'space-y-1'}>{blocks}</div>;
};
