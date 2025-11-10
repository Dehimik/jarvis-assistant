import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import rehypeRaw from 'rehype-raw';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

// робочий фолбек — any, щоб не було TS-помилок
const CodeBlock = ({ inline, className, children, ...props }: any) => {
  if (inline) return <code className="bg-gray-100 px-1 rounded text-sm" {...props}>{children}</code>;

  const cls = typeof className === 'string' ? className : '';
  const m = /language-(\w+)/.exec(cls);
  const lang = m ? m[1] : undefined;

  return (
    <div className="my-4">
      <SyntaxHighlighter PreTag="div" style={oneDark} language={lang} {...props}>
        {String(children).replace(/\n$/, '')}
      </SyntaxHighlighter>
    </div>
  );
};

// покращені рендерери для елементів, щоб краще контролювати вигляд
const components: Partial<any> = {
  code: CodeBlock,
  p: ({ node, children, ...props }: any) => <p className="leading-7 my-2" {...props}>{children}</p>,
  a: ({ href, children, ...props }: any) => (
    <a className="text-blue-600 underline" href={href} target={href?.startsWith('http') ? '_blank' : undefined} rel="noreferrer" {...props}>
      {children}
    </a>
  ),
  img: ({ src, alt, title, ...props }: any) => (
    // адаптивні зображення
    <img src={src} alt={alt} title={title} className="max-w-full h-auto rounded-md my-2" {...props} />
  ),
  table: ({ children, ...props }: any) => (
    <div className="overflow-x-auto my-4">
      <table className="min-w-full table-auto border-collapse" {...props}>
        {children}
      </table>
    </div>
  ),
  th: ({ children, ...props }: any) => <th className="text-left px-3 py-2 border-b" {...props}>{children}</th>,
  td: ({ children, ...props }: any) => <td className="px-3 py-2 align-top border-b" {...props}>{children}</td>,
  ul: ({ children, ...props }: any) => <ul className="list-disc ml-6 my-2" {...props}>{children}</ul>,
  ol: ({ children, ...props }: any) => <ol className="list-decimal ml-6 my-2" {...props}>{children}</ol>,
  blockquote: ({ children, ...props }: any) => <blockquote className="border-l-4 pl-4 italic text-gray-700 my-3" {...props}>{children}</blockquote>,
  h1: ({ children, ...props }: any) => <h1 className="text-3xl font-bold my-4" {...props}>{children}</h1>,
  h2: ({ children, ...props }: any) => <h2 className="text-2xl font-semibold my-3" {...props}>{children}</h2>,
  h3: ({ children, ...props }: any) => <h3 className="text-xl font-medium my-2" {...props}>{children}</h3>,
};

export default function ReadmePage(): JSX.Element {
  const [markdown, setMarkdown] = useState<string>('');
  const [useRaw, setUseRaw] = useState<boolean>(false);

  useEffect(() => {
    fetch('/About.md')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((text) => {
        console.log('[DEBUG] About.md length', text.length);
        // Якщо в MD є фронтматтер (---) — прибираємо
        const noFront = text.replace(/^---[\s\S]*?---\s*/, '');
        // Якщо є HTML-теги, вмикаємо rehypeRaw (обережно: XSS)
        const hasHTML = /<([a-zA-Z]+)(\s|>)/.test(noFront);
        setUseRaw(Boolean(hasHTML));
        setMarkdown(noFront);
      })
      .catch((err) => {
        console.error('Error fetching About.md', err);
      });
  }, []);

  return (
    <div className="max-w-none p-4 overflow-y-auto h-full">
      {/* Якщо хочеш докинути prose — додавай, але іноді краще без нього */}
      <div className="prose lg:prose-lg dark:prose-invert">
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkBreaks]}
          rehypePlugins={useRaw ? [rehypeRaw] : []}
          components={components}
        >
          {markdown}
        </ReactMarkdown>
      </div>
    </div>
  );
}
