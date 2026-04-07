'use client'

import { useState } from 'react'
import { Bot, Send, Loader2, Sparkles, Zap, Brain, Code } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const examplePrompts = [
  'A customer support bot for my e-commerce store that can track orders and answer FAQs',
  'A personal fitness coach that creates workout plans and tracks progress',
  'A language learning tutor that helps me practice Spanish with conversations',
  'A project management assistant that helps teams track tasks and deadlines',
]

const intelligenceLevels = [
  {
    id: 'standard',
    label: 'Standard',
    description: 'Fast, reliable responses',
    icon: Zap,
  },
  {
    id: 'advanced',
    label: 'Advanced',
    description: 'Complex reasoning capabilities',
    icon: Brain,
  },
  {
    id: 'creative',
    label: 'Creative',
    description: 'For unique, innovative bots',
    icon: Sparkles,
  },
]

export function BotBuilder() {
  const [prompt, setPrompt] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedBot, setGeneratedBot] = useState<any>(null)
  const [selectedLevel, setSelectedLevel] = useState('advanced')

  const handleGenerate = async () => {
    if (!prompt.trim()) return
    
    setIsGenerating(true)
    setGeneratedBot(null)
    
    // Simulate API call - in production this would call the backend
    await new Promise((resolve) => setTimeout(resolve, 2500))
    
    // Simulated response
    setGeneratedBot({
      bot_name: 'SmartAssistant',
      bot_description: 'An intelligent assistant designed to help with your specific needs.',
      features: [
        { name: 'Natural Conversations', description: 'Engages in human-like dialogue', ai_powered: true },
        { name: 'Context Memory', description: 'Remembers conversation history', ai_powered: true },
        { name: 'Smart Suggestions', description: 'Proactively offers helpful tips', ai_powered: true },
      ],
      commands: [
        { command: '/start', description: 'Begin interacting with the bot' },
        { command: '/help', description: 'Get a list of available commands' },
        { command: '/settings', description: 'Configure your preferences' },
      ],
      personality: {
        tone: 'friendly',
        traits: ['helpful', 'knowledgeable', 'patient'],
      },
    })
    
    setIsGenerating(false)
  }

  const handleExampleClick = (example: string) => {
    setPrompt(example)
  }

  return (
    <section id="builder" className="border-b border-border/40 bg-muted/30 py-16 md:py-24">
      <div className="container mx-auto px-4">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl">
            Build Your Bot
          </h2>
          <p className="mb-8 text-muted-foreground">
            Describe what you want your bot to do, and our AI will create it for you.
          </p>
        </div>

        <div className="mx-auto max-w-4xl">
          <Card className="border-2 border-border/50 shadow-lg">
            <CardHeader className="pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
                  <Bot className="h-5 w-5 text-primary-foreground" />
                </div>
                <div>
                  <CardTitle>AI Bot Builder</CardTitle>
                  <CardDescription>Powered by advanced language models</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Intelligence Level Selection */}
              <div className="space-y-3">
                <label className="text-sm font-medium">Intelligence Level</label>
                <div className="grid grid-cols-3 gap-3">
                  {intelligenceLevels.map((level) => {
                    const Icon = level.icon
                    return (
                      <button
                        key={level.id}
                        onClick={() => setSelectedLevel(level.id)}
                        className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 text-center transition-all ${
                          selectedLevel === level.id
                            ? 'border-primary bg-primary/5'
                            : 'border-border hover:border-primary/50'
                        }`}
                      >
                        <Icon className={`h-5 w-5 ${selectedLevel === level.id ? 'text-primary' : 'text-muted-foreground'}`} />
                        <span className="text-sm font-medium">{level.label}</span>
                        <span className="text-xs text-muted-foreground">{level.description}</span>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Prompt Input */}
              <div className="space-y-3">
                <label className="text-sm font-medium">Describe your bot</label>
                <div className="relative">
                  <Textarea
                    placeholder="E.g., A customer support bot that answers questions about my products, tracks orders, and collects feedback..."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    className="min-h-[120px] resize-none pr-12"
                  />
                  <Button
                    size="icon"
                    className="absolute bottom-3 right-3"
                    onClick={handleGenerate}
                    disabled={!prompt.trim() || isGenerating}
                  >
                    {isGenerating ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              {/* Example Prompts */}
              <div className="space-y-3">
                <label className="text-sm font-medium text-muted-foreground">Try an example</label>
                <div className="flex flex-wrap gap-2">
                  {examplePrompts.map((example, index) => (
                    <button
                      key={index}
                      onClick={() => handleExampleClick(example)}
                      className="rounded-full border border-border bg-background px-3 py-1.5 text-xs transition-colors hover:bg-muted"
                    >
                      {example.slice(0, 40)}...
                    </button>
                  ))}
                </div>
              </div>

              {/* Generation Progress */}
              {isGenerating && (
                <div className="flex items-center gap-3 rounded-lg bg-primary/5 p-4">
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                  <div>
                    <p className="font-medium">Creating your bot...</p>
                    <p className="text-sm text-muted-foreground">
                      Analyzing requirements and generating configuration
                    </p>
                  </div>
                </div>
              )}

              {/* Generated Bot Preview */}
              {generatedBot && (
                <div className="space-y-4 rounded-lg border border-border bg-background p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <Bot className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <h3 className="font-semibold">{generatedBot.bot_name}</h3>
                        <p className="text-sm text-muted-foreground">{generatedBot.bot_description}</p>
                      </div>
                    </div>
                    <Badge variant="secondary">
                      {selectedLevel.charAt(0).toUpperCase() + selectedLevel.slice(1)}
                    </Badge>
                  </div>

                  <Tabs defaultValue="features" className="w-full">
                    <TabsList className="grid w-full grid-cols-3">
                      <TabsTrigger value="features">Features</TabsTrigger>
                      <TabsTrigger value="commands">Commands</TabsTrigger>
                      <TabsTrigger value="personality">Personality</TabsTrigger>
                    </TabsList>
                    <TabsContent value="features" className="mt-4 space-y-2">
                      {generatedBot.features.map((feature: any, index: number) => (
                        <div key={index} className="flex items-start gap-3 rounded-lg bg-muted/50 p-3">
                          <div className="mt-0.5 h-2 w-2 rounded-full bg-primary" />
                          <div>
                            <p className="font-medium">{feature.name}</p>
                            <p className="text-sm text-muted-foreground">{feature.description}</p>
                          </div>
                          {feature.ai_powered && (
                            <Badge variant="outline" className="ml-auto shrink-0">
                              AI-Powered
                            </Badge>
                          )}
                        </div>
                      ))}
                    </TabsContent>
                    <TabsContent value="commands" className="mt-4 space-y-2">
                      {generatedBot.commands.map((cmd: any, index: number) => (
                        <div key={index} className="flex items-center gap-3 rounded-lg bg-muted/50 p-3">
                          <code className="rounded bg-background px-2 py-1 text-sm font-mono text-primary">
                            {cmd.command}
                          </code>
                          <span className="text-sm text-muted-foreground">{cmd.description}</span>
                        </div>
                      ))}
                    </TabsContent>
                    <TabsContent value="personality" className="mt-4">
                      <div className="space-y-4 rounded-lg bg-muted/50 p-4">
                        <div>
                          <p className="text-sm font-medium">Tone</p>
                          <p className="text-muted-foreground capitalize">{generatedBot.personality.tone}</p>
                        </div>
                        <div>
                          <p className="mb-2 text-sm font-medium">Traits</p>
                          <div className="flex flex-wrap gap-2">
                            {generatedBot.personality.traits.map((trait: string, index: number) => (
                              <Badge key={index} variant="secondary" className="capitalize">
                                {trait}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                    </TabsContent>
                  </Tabs>

                  <div className="flex gap-3 pt-2">
                    <Button className="flex-1">
                      <Code className="mr-2 h-4 w-4" />
                      Deploy Bot
                    </Button>
                    <Button variant="outline">
                      Customize
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  )
}
