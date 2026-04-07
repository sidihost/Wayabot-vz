'use client'

import { useState } from 'react'
import { ArrowUpRight, Bot, Headphones, BookOpen, Code, Dumbbell, MessageCircle, Briefcase, Users } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

const categories = ['All', 'Business', 'Education', 'Health', 'Support', 'Creative']

const templates = [
  {
    id: 'customer-support',
    name: 'Customer Support',
    description: 'Handle inquiries, track orders, and provide 24/7 automated support.',
    category: 'Business',
    icon: Headphones,
    featured: true,
    features: ['Ticket Creation', 'FAQ Answers', 'Order Tracking'],
  },
  {
    id: 'personal-assistant',
    name: 'Personal Assistant',
    description: 'Manage reminders, notes, tasks, and schedule with smart suggestions.',
    category: 'Business',
    icon: Bot,
    featured: true,
    features: ['Reminders', 'Task Management', 'Calendar'],
  },
  {
    id: 'language-tutor',
    name: 'Language Tutor',
    description: 'Interactive language learning with vocabulary, grammar, and conversation practice.',
    category: 'Education',
    icon: BookOpen,
    features: ['Vocabulary', 'Grammar', 'Conversation'],
  },
  {
    id: 'code-assistant',
    name: 'Code Assistant',
    description: 'Debug code, explain concepts, and provide best practice recommendations.',
    category: 'Education',
    icon: Code,
    features: ['Code Review', 'Debugging', 'Explanations'],
  },
  {
    id: 'fitness-coach',
    name: 'Fitness Coach',
    description: 'Personalized workout plans, nutrition tips, and progress tracking.',
    category: 'Health',
    icon: Dumbbell,
    features: ['Workouts', 'Nutrition', 'Progress'],
  },
  {
    id: 'faq-bot',
    name: 'FAQ Bot',
    description: 'Answer frequently asked questions with intelligent context understanding.',
    category: 'Support',
    icon: MessageCircle,
    features: ['Knowledge Base', 'Smart Search', 'Escalation'],
  },
  {
    id: 'hr-assistant',
    name: 'HR Assistant',
    description: 'Handle employee queries, onboarding, and policy information.',
    category: 'Business',
    icon: Briefcase,
    features: ['Onboarding', 'Policies', 'Leave Requests'],
  },
  {
    id: 'community-manager',
    name: 'Community Manager',
    description: 'Moderate discussions, welcome new members, and organize events.',
    category: 'Support',
    icon: Users,
    features: ['Moderation', 'Welcome Flow', 'Events'],
  },
]

export function TemplatesSection() {
  const [selectedCategory, setSelectedCategory] = useState('All')

  const filteredTemplates = selectedCategory === 'All'
    ? templates
    : templates.filter(t => t.category === selectedCategory)

  return (
    <section id="templates" className="bg-muted/30 py-16 md:py-24">
      <div className="container mx-auto px-4">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl">
            Start with a Template
          </h2>
          <p className="mb-8 text-lg text-muted-foreground">
            Jumpstart your bot development with pre-built templates designed for common use cases.
          </p>
        </div>

        {/* Category Filter */}
        <div className="mb-8 flex flex-wrap items-center justify-center gap-2">
          {categories.map((category) => (
            <Button
              key={category}
              variant={selectedCategory === category ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(category)}
              className="rounded-full"
            >
              {category}
            </Button>
          ))}
        </div>

        {/* Templates Grid */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {filteredTemplates.map((template) => {
            const Icon = template.icon
            return (
              <Card 
                key={template.id} 
                className="group relative overflow-hidden transition-all hover:border-primary/50 hover:shadow-lg"
              >
                {template.featured && (
                  <div className="absolute right-3 top-3">
                    <Badge variant="secondary" className="bg-primary/10 text-primary">
                      Popular
                    </Badge>
                  </div>
                )}
                <CardHeader>
                  <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-muted transition-colors group-hover:bg-primary/10">
                    <Icon className="h-6 w-6 text-muted-foreground transition-colors group-hover:text-primary" />
                  </div>
                  <CardTitle className="text-lg">{template.name}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <CardDescription className="line-clamp-2">
                    {template.description}
                  </CardDescription>
                  <div className="flex flex-wrap gap-1.5">
                    {template.features.map((feature, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {feature}
                      </Badge>
                    ))}
                  </div>
                  <Button variant="ghost" className="w-full justify-between group-hover:bg-muted">
                    Use Template
                    <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </Button>
                </CardContent>
              </Card>
            )
          })}
        </div>

        <div className="mt-12 text-center">
          <Button variant="outline" size="lg">
            View All Templates
          </Button>
        </div>
      </div>
    </section>
  )
}
