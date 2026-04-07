import { 
  Brain, 
  MessageSquare, 
  Mic, 
  Heart, 
  Zap, 
  Shield, 
  Globe, 
  BarChart3 
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const features = [
  {
    icon: Brain,
    title: 'Advanced AI Intelligence',
    description: 'Powered by state-of-the-art language models for natural, context-aware conversations that understand user intent.',
    highlight: true,
  },
  {
    icon: MessageSquare,
    title: 'Natural Language Processing',
    description: 'Bots understand and respond to messages naturally, handling complex queries with ease.',
  },
  {
    icon: Mic,
    title: 'Voice AI Integration',
    description: 'Text-to-speech and speech-to-text capabilities with 12+ premium voices and voice cloning.',
  },
  {
    icon: Heart,
    title: 'Emotion Detection',
    description: 'Hume AI integration for empathic responses that adapt to user emotional states.',
  },
  {
    icon: Zap,
    title: 'Instant Deployment',
    description: 'Deploy your bot with one click. No server setup or configuration required.',
  },
  {
    icon: Shield,
    title: 'Enterprise Security',
    description: 'End-to-end encryption, rate limiting, and comprehensive access controls.',
  },
  {
    icon: Globe,
    title: 'Multi-language Support',
    description: 'Automatic translation and language detection for global reach.',
  },
  {
    icon: BarChart3,
    title: 'Analytics Dashboard',
    description: 'Track conversations, user engagement, and bot performance in real-time.',
  },
]

export function FeaturesSection() {
  return (
    <section id="features" className="border-b border-border/40 py-16 md:py-24">
      <div className="container mx-auto px-4">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl">
            Everything you need to build intelligent bots
          </h2>
          <p className="mb-12 text-lg text-muted-foreground">
            A complete platform with AI capabilities, voice features, emotion detection, and more.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {features.map((feature, index) => {
            const Icon = feature.icon
            return (
              <Card 
                key={index} 
                className={`group transition-all hover:border-primary/50 hover:shadow-md ${
                  feature.highlight ? 'md:col-span-2 lg:col-span-2 lg:row-span-2' : ''
                }`}
              >
                <CardHeader>
                  <div className={`mb-4 flex h-12 w-12 items-center justify-center rounded-lg transition-colors ${
                    feature.highlight 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary'
                  }`}>
                    <Icon className="h-6 w-6" />
                  </div>
                  <CardTitle className={feature.highlight ? 'text-2xl' : ''}>{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className={feature.highlight ? 'text-base' : ''}>
                    {feature.description}
                  </CardDescription>
                  {feature.highlight && (
                    <div className="mt-6 grid grid-cols-3 gap-4 text-center">
                      <div>
                        <p className="text-2xl font-bold text-primary">4B+</p>
                        <p className="text-sm text-muted-foreground">Parameters</p>
                      </div>
                      <div>
                        <p className="text-2xl font-bold text-primary">{'<'}100ms</p>
                        <p className="text-sm text-muted-foreground">Response Time</p>
                      </div>
                      <div>
                        <p className="text-2xl font-bold text-primary">99.9%</p>
                        <p className="text-sm text-muted-foreground">Uptime</p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>
    </section>
  )
}
