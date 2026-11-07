/**
 * Aria World & Cultural Awareness Coordinator.
 * Dynamically tracks real-world time, calendar dates, Indian & global festivals,
 * proactive greetings, and festival safety intelligence.
 */

export interface FestivalEvent {
  id: string;
  name: string;
  greetingText: string;
  tamilGreeting?: string;
  safetyAdvice?: string[];
  dateCheck: (now: Date) => boolean;
}

export class AwarenessCoordinator {
  private greetingHistory: Set<string> = new Set();
  private festivals: FestivalEvent[] = [];

  constructor() {
    this.initFestivals();
  }

  private initFestivals(): void {
    this.festivals = [
      {
        id: 'new_year',
        name: 'New Year',
        greetingText: 'Happy New Year, Harshan! Wishing you a year filled with new opportunities, joy, and achievements.',
        tamilGreeting: 'இனிய புத்தாண்டு நல்வாழ்த்துகள் ஹர்ஷன்!',
        dateCheck: (d) => d.getMonth() === 0 && d.getDate() === 1,
      },
      {
        id: 'pongal',
        name: 'Pongal',
        greetingText: 'Iniya Pongal Nalvazhthukkal, Harshan! Wishing you and your family abundant happiness, prosperity, and sweet moments.',
        tamilGreeting: 'இனிய பொங்கல் நல்வாழ்த்துகள் ஹர்ஷன்! தை பிறந்தால் வழி பிறக்கும்.',
        dateCheck: (d) => d.getMonth() === 0 && d.getDate() >= 14 && d.getDate() <= 17,
      },
      {
        id: 'republic_day',
        name: 'Republic Day',
        greetingText: 'Happy Republic Day, Harshan! Celebrating the spirit, unity, and democracy of our nation.',
        dateCheck: (d) => d.getMonth() === 0 && d.getDate() === 26,
      },
      {
        id: 'tamil_new_year',
        name: 'Tamil New Year',
        greetingText: 'Iniya Tamizh Puthandu Nalvazhthukkal, Harshan! May this new year bring endless peace and success.',
        tamilGreeting: 'இனிய தமிழ் புத்தாண்டு நல்வாழ்த்துகள் ஹர்ஷன்!',
        dateCheck: (d) => d.getMonth() === 3 && (d.getDate() === 14 || d.getDate() === 15),
      },
      {
        id: 'independence_day',
        name: 'Independence Day',
        greetingText: 'Happy Independence Day, Harshan! Celebrating freedom, progress, and unity.',
        dateCheck: (d) => d.getMonth() === 7 && d.getDate() === 15,
      },
      {
        id: 'diwali',
        name: 'Diwali',
        greetingText: 'Happy Diwali, Harshan! Wishing you and your family divine happiness, warmth, and prosperity. Have a wonderful celebration!',
        tamilGreeting: 'இனிய தீபாவளி நல்வாழ்த்துகள் ஹர்ஷன்!',
        safetyAdvice: [
          'Maintain a safe distance from fireworks while lighting them.',
          'Always keep a bucket of water, sand, or a fire extinguisher nearby.',
          'Never light fireworks while holding them in your hands or inside containers.',
          'Never attempt to relight failed fireworks or duds.',
          'Keep pets and animals indoors in quiet, comfortable rooms.',
          'Avoid bursting crackers near hospitals, elderly homes, and quiet zones.',
          'In case of any emergency in India, dial 112 immediately.',
        ],
        dateCheck: (d) => {
          // Dynamic October/November festival window
          const month = d.getMonth();
          return month === 9 || month === 10;
        },
      },
      {
        id: 'christmas',
        name: 'Christmas',
        greetingText: 'Merry Christmas, Harshan! Wishing you peace, cheer, and wonderful celebrations with family.',
        dateCheck: (d) => d.getMonth() === 11 && d.getDate() === 25,
      },
    ];
  }

  /**
   * Return today's special occasions and verified real-world context.
   */
  public getTodayContext(now: Date = new Date()): {
    dateString: string;
    dayOfWeek: string;
    timeString: string;
    specialEvent?: FestivalEvent;
  } {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

    const dayOfWeek = days[now.getDay()];
    const dateString = `${months[now.getMonth()]} ${now.getDate()}, ${now.getFullYear()}`;
    const hours = now.getHours();
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours % 12 || 12;
    const timeString = `${displayHours}:${minutes} ${ampm}`;

    const activeFestivals = this.festivals.filter(f => f.dateCheck(now));
    return {
      dateString,
      dayOfWeek,
      timeString,
      specialEvent: activeFestivals[0],
    };
  }

  /**
   * Check if a festival greeting should be proactively spoken (without repetition).
   */
  public getProactiveGreeting(now: Date = new Date()): string | null {
    const ctx = this.getTodayContext(now);
    if (!ctx.specialEvent) return null;

    const key = `${ctx.specialEvent.id}_${now.getFullYear()}_${now.getMonth()}_${now.getDate()}`;
    if (this.greetingHistory.has(key)) return null;

    this.greetingHistory.add(key);
    let msg = ctx.specialEvent.greetingText;
    if (ctx.specialEvent.safetyAdvice && ctx.specialEvent.safetyAdvice.length > 0) {
      msg += ` Remember to celebrate safely: ${ctx.specialEvent.safetyAdvice[0]}`;
    }
    return msg;
  }

  /**
   * Return festival safety guidelines.
   */
  public getSafetyAdvice(topic: string = 'diwali'): string[] {
    const fest = this.festivals.find(f => f.id === topic.toLowerCase() || topic.toLowerCase().includes(f.id));
    return fest?.safetyAdvice || [
      'Maintain safe distances and keep emergency equipment accessible.',
      'For any medical or fire emergency in India, immediately dial 112.',
    ];
  }
}
