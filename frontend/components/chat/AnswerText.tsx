interface AnswerTextProps {
  content: string;
}

// Backend prompt template wraps answers in a legal-memo shape ("**Trả lời:**",
// "**Nguồn tham khảo:** [1] ...") meant for citation traceability. The source
// list is redundant here — SourcePill chips already render it below the
// bubble — so it's stripped for a plainer, chat-native read.
function cleanAnswer(raw: string): string {
  let text = raw;
  text = text.replace(/^\*\*Trả lời:\*\*\s*/i, "");
  text = text.replace(/\*\*Nguồn tham khảo:\*\*[\s\S]*?(?=\n\*\*|\n*$)/i, "");
  text = text.replace(/\s*\[\d+\]/g, "");
  text = text.replace(/\n{3,}/g, "\n\n").trim();
  return text;
}

function renderInline(text: string, keyPrefix: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>
    ) : (
      <span key={`${keyPrefix}-${i}`}>{part}</span>
    ),
  );
}

export function AnswerText({ content }: AnswerTextProps) {
  const paragraphs = cleanAnswer(content).split(/\n\n+/);
  return (
    <div className="flex flex-col gap-2">
      {paragraphs.map((paragraph, i) => (
        <p key={i} className="whitespace-pre-wrap">
          {renderInline(paragraph, `p${i}`)}
        </p>
      ))}
    </div>
  );
}
