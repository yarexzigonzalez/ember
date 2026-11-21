import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'

const preview = [
  { status: 'Saved', items: ['Stripe · Backend intern', 'Notion · New grad'] },
  { status: 'Applied', items: ['Figma · Product intern'] },
  { status: 'Interview', items: ['Cloudflare · SWE intern'] },
]

export function Landing() {
  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-5 py-6 md:px-8">
      <header className="flex items-center justify-between">
        <span className="font-serif text-2xl">Ember</span>
        <div className="flex gap-2">
          <Button asChild variant="ghost" size="sm">
            <Link to="/login">Log in</Link>
          </Button>
          <Button asChild size="sm">
            <Link to="/signup">Sign up</Link>
          </Button>
        </div>
      </header>

      <section className="grid flex-1 items-center gap-12 py-16 md:grid-cols-[1.1fr_0.9fr]">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <p className="font-mono text-xs tracking-[0.22em] text-ember-2 uppercase">
            Job search, kept warm
          </p>
          <h1 className="mt-4 max-w-xl font-serif text-5xl leading-[1.05] text-cream md:text-6xl">
            Don't let the pipeline go cold.
          </h1>
          <p className="mt-5 max-w-md text-lg text-tan">
            Applications, follow-ups, and the numbers on what actually gets a reply. Built
            for one person running their own search.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild>
              <Link to="/demo">
                View live demo <ArrowRight size={16} />
              </Link>
            </Button>
            <Button asChild variant="quiet">
              <Link to="/login">Log in</Link>
            </Button>
          </div>
        </motion.div>

        <div className="grid grid-cols-3 gap-3">
          {preview.map((column) => (
            <div
              key={column.status}
              className="rounded-2xl border border-line bg-raised/80 p-3"
            >
              <p className="font-mono text-[11px] tracking-wide text-tan uppercase">
                {column.status}
              </p>
              <div className="mt-3 grid gap-2">
                {column.items.map((item) => (
                  <div
                    key={item}
                    className="rounded-xl border border-line bg-raised-2 px-3 py-3 text-sm"
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
