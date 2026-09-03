import Link from "next/link";
import { LineChart, ShieldCheck, FlaskConical, Database } from "lucide-react";
import { TickerSearch } from "@/components/search/TickerSearch";
import { Card, CardHeader } from "@/components/ui/Card";
import { POPULAR_TICKERS } from "@/lib/constants";

export default function OverviewPage() {
  return (
    <div className="mx-auto max-w-[1100px] px-4 sm:px-6 py-12 sm:py-16 flex flex-col gap-14">
      <section className="flex flex-col gap-6 items-start">
        <span className="text-xs font-medium tracking-widest uppercase text-accent">
          Quantitative Research Terminal
        </span>
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-text-primary max-w-2xl">
          Transparent, rules-based stock analysis built on real market data.
        </h1>
        <p className="text-text-secondary text-base max-w-2xl leading-relaxed">
          Stock Analyst retrieves live and historical price data from Yahoo Finance and runs it through
          a documented, deterministic scoring model to classify each ticker&apos;s technical state as
          Strong Buy, Buy, Hold, Sell, or Strong Sell — with every contributing factor shown, not hidden
          behind a black box.
        </p>

        <div className="w-full max-w-xl">
          <TickerSearch autoFocus />
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-xs text-text-muted mr-1">Try:</span>
          {POPULAR_TICKERS.map((t) => (
            <Link
              key={t}
              href={`/analysis?ticker=${t}`}
              className="font-mono text-xs px-2.5 py-1 rounded border border-border-strong text-text-secondary hover:text-text-primary hover:border-accent transition-colors"
            >
              {t}
            </Link>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <Database size={18} className="text-accent mb-3" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-text-primary mb-1.5">Real market data, labeled honestly</h3>
          <p className="text-xs text-text-muted leading-relaxed">
            Every price, indicator, and signal is computed from data actually retrieved from Yahoo
            Finance via <code className="font-mono">yfinance</code> — never fabricated. Every response is
            tagged Live, Delayed, Market Closed, Historical, or Unavailable so you always know what
            you&apos;re looking at.
          </p>
        </Card>
        <Card>
          <FlaskConical size={18} className="text-accent mb-3" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-text-primary mb-1.5">Deterministic, documented model</h3>
          <p className="text-xs text-text-muted leading-relaxed">
            No LLM, no black box. Trend, momentum, volume, and volatility factors are combined through a
            fixed, published point system into a 0–100 score. The same data always produces the same
            score — and every factor behind it is shown on the analysis page.
          </p>
        </Card>
        <Card>
          <ShieldCheck size={18} className="text-accent mb-3" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-text-primary mb-1.5">Research tool, not advice</h3>
          <p className="text-xs text-text-muted leading-relaxed">
            BUY/HOLD/SELL means only that current data satisfies this model&apos;s predefined conditions
            for that bucket. It is not personalized financial advice, and it does not predict future
            returns. Always do your own research.
          </p>
        </Card>
      </section>

      <section>
        <Card>
          <CardHeader
            title="How the signal is built"
            subtitle="A short summary — full methodology is documented in the project README"
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm text-text-secondary leading-relaxed">
            <div>
              <h4 className="text-text-primary font-medium mb-1.5 flex items-center gap-2">
                <LineChart size={15} className="text-accent" /> Scoring
              </h4>
              <p className="text-xs">
                Trend (price vs. 20/50/200-day SMAs), momentum (RSI, MACD, rate of change), volume
                confirmation, and volatility regime each contribute points on a fixed scale. Points sum to
                a raw score, which is normalized to 0–100 based on the actual range of factors available
                for that stock.
              </p>
            </div>
            <div>
              <h4 className="text-text-primary font-medium mb-1.5 flex items-center gap-2">
                <ShieldCheck size={15} className="text-accent" /> Confidence, not certainty
              </h4>
              <p className="text-xs">
                A separate confidence score reflects how complete the data is and how much the
                individual factors agree with each other — it is explicitly not a probability that the
                price will move in any direction.
              </p>
            </div>
          </div>
        </Card>
      </section>
    </div>
  );
}
