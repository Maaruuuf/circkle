import { HomeGate } from "@/components/HomeGate";
import { Landing } from "@/components/Landing";

export default function HomePage() {
  return <HomeGate landing={<Landing />} />;
}
