import { Header } from '@/components/header'
import { HeroSection } from '@/components/hero-section'
import { BotBuilder } from '@/components/bot-builder'
import { FeaturesSection } from '@/components/features-section'
import { TemplatesSection } from '@/components/templates-section'
import { Footer } from '@/components/footer'

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header />
      <main className="flex-1">
        <HeroSection />
        <BotBuilder />
        <FeaturesSection />
        <TemplatesSection />
      </main>
      <Footer />
    </div>
  )
}
