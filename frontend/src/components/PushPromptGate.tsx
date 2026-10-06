import PushPrompt from './PushPrompt';
import { useSessionActive } from '../lib/session';

export default function PushPromptGate() {
  const connecte = useSessionActive();
  return connecte ? <PushPrompt /> : null;
}
