import { ChatView } from "../components/ChatView";
import { PageHeader } from "../ui/primitives";

export function AiAssistantPage() {
  return (
    <div>
      <PageHeader title="AI Assistant" subtitle="Talk to DISHA — Hindi, English or Hinglish. Every action waits for your approval." />
      <ChatView />
    </div>
  );
}
