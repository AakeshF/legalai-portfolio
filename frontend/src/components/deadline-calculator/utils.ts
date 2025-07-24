import { Deadline, DeadlineTemplate, CourtHoliday } from './types';
import { format, addDays, isWeekend, isSameDay, addBusinessDays } from 'date-fns';

// Local deadline templates for offline fallback
export const LOCAL_DEADLINE_TEMPLATES: Record<string, DeadlineTemplate[]> = {
  personal_injury: [
    {
      title: 'Statute of Limitations',
      daysFromTrigger: 730, // 2 years
      type: 'statute_of_limitations',
      isBusinessDays: false,
      severity: 'critical',
      citation: 'CCP § 335.1'
    },
    {
      title: 'File Complaint',
      daysFromTrigger: 700,
      type: 'filing',
      isBusinessDays: true,
      severity: 'high'
    },
    {
      title: 'Serve Defendant',
      daysFromTrigger: 60,
      type: 'service',
      isBusinessDays: true,
      severity: 'high',
      citation: 'CCP § 583.210'
    },
    {
      title: 'Initial Case Management Conference',
      daysFromTrigger: 180,
      type: 'hearing',
      isBusinessDays: true,
      severity: 'medium'
    }
  ],
  contract: [
    {
      title: 'Statute of Limitations (Written)',
      daysFromTrigger: 1460, // 4 years
      type: 'statute_of_limitations',
      isBusinessDays: false,
      severity: 'critical',
      citation: 'CCP § 337'
    },
    {
      title: 'Statute of Limitations (Oral)',
      daysFromTrigger: 730, // 2 years
      type: 'statute_of_limitations',
      isBusinessDays: false,
      severity: 'critical',
      citation: 'CCP § 339'
    },
    {
      title: 'Demand Letter',
      daysFromTrigger: 30,
      type: 'notice',
      isBusinessDays: true,
      severity: 'medium'
    }
  ],
  employment: [
    {
      title: 'EEOC Filing Deadline',
      daysFromTrigger: 300,
      type: 'filing',
      isBusinessDays: false,
      severity: 'critical',
      citation: '42 U.S.C. § 2000e-5(e)(1)'
    },
    {
      title: 'State Agency Filing (DFEH)',
      daysFromTrigger: 365,
      type: 'filing',
      isBusinessDays: false,
      severity: 'critical',
      citation: 'Gov. Code § 12960'
    }
  ]
};

export function calculateDeadlineDate(
  triggerDate: Date,
  daysFromTrigger: number,
  isBusinessDays: boolean,
  holidays: CourtHoliday[] = []
): Date {
  if (!isBusinessDays) {
    return addDays(triggerDate, daysFromTrigger);
  }

  let date = new Date(triggerDate);
  let daysAdded = 0;

  while (daysAdded < daysFromTrigger) {
    date = addDays(date, 1);
    
    // Skip weekends
    if (isWeekend(date)) {
      continue;
    }
    
    // Skip holidays
    const isHoliday = holidays.some(holiday => 
      isSameDay(new Date(holiday.date), date) && holiday.isObserved
    );
    
    if (isHoliday) {
      continue;
    }
    
    daysAdded++;
  }

  return date;
}

export function getDeadlineSeverity(deadline: Deadline): 'critical' | 'high' | 'medium' | 'low' {
  const daysUntil = Math.ceil((deadline.date.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));
  
  // Override with deadline's inherent severity if critical
  if (deadline.severity === 'critical') {
    return 'critical';
  }
  
  // Adjust severity based on time remaining
  if (daysUntil <= 7) {
    return 'critical';
  } else if (daysUntil <= 30) {
    return 'high';
  } else if (daysUntil <= 90) {
    return 'medium';
  }
  
  return deadline.severity;
}

export function formatDeadlineDate(date: Date): string {
  return format(date, 'MMM d, yyyy');
}

export function getDaysUntilDeadline(deadline: Date): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const deadlineDate = new Date(deadline);
  deadlineDate.setHours(0, 0, 0, 0);
  
  const diffTime = deadlineDate.getTime() - today.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  return diffDays;
}

export function generateDeadlineId(title: string, date: Date): string {
  return `${title.toLowerCase().replace(/\s+/g, '-')}-${date.getTime()}`;
}

export function sortDeadlinesByDate(deadlines: Deadline[]): Deadline[] {
  return [...deadlines].sort((a, b) => a.date.getTime() - b.date.getTime());
}

export function groupDeadlinesByMonth(deadlines: Deadline[]): Record<string, Deadline[]> {
  const grouped: Record<string, Deadline[]> = {};
  
  deadlines.forEach(deadline => {
    const monthKey = format(deadline.date, 'MMMM yyyy');
    if (!grouped[monthKey]) {
      grouped[monthKey] = [];
    }
    grouped[monthKey].push(deadline);
  });
  
  return grouped;
}

export function exportToICS(deadlines: Deadline[]): string {
  const icsLines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Legal AI//Deadline Calculator//EN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH'
  ];
  
  deadlines.forEach(deadline => {
    const startDate = format(deadline.date, "yyyyMMdd'T'HHmmss");
    const uid = `${deadline.id}@legal-ai.com`;
    
    icsLines.push(
      'BEGIN:VEVENT',
      `UID:${uid}`,
      `DTSTAMP:${format(new Date(), "yyyyMMdd'T'HHmmss'Z'")}`,
      `DTSTART:${startDate}`,
      `DTEND:${startDate}`,
      `SUMMARY:${deadline.title}`,
      deadline.description ? `DESCRIPTION:${deadline.description.replace(/\n/g, '\\n')}` : '',
      deadline.citation ? `LOCATION:${deadline.citation}` : '',
      `CATEGORIES:${deadline.type.toUpperCase()}`,
      `PRIORITY:${deadline.severity === 'critical' ? 1 : deadline.severity === 'high' ? 2 : 3}`,
      'END:VEVENT'
    );
  });
  
  icsLines.push('END:VCALENDAR');
  
  return icsLines.filter(line => line).join('\r\n');
}

export function downloadICSFile(deadlines: Deadline[], filename: string = 'legal-deadlines.ics') {
  const icsContent = exportToICS(deadlines);
  const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
  const url = window.URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  window.URL.revokeObjectURL(url);
}

// Calculate deadlines locally when MCP is unavailable
export function calculateDeadlinesLocally(
  triggerDate: Date,
  caseType: string,
  jurisdiction: { state: string; county?: string }
): Deadline[] {
  const templates = LOCAL_DEADLINE_TEMPLATES[caseType] || [];
  
  return templates.map(template => {
    const deadlineDate = calculateDeadlineDate(
      triggerDate,
      template.daysFromTrigger,
      template.isBusinessDays
    );
    
    return {
      id: generateDeadlineId(template.title, deadlineDate),
      title: template.title,
      date: deadlineDate,
      daysFromTrigger: template.daysFromTrigger,
      type: template.type,
      severity: template.severity,
      jurisdiction,
      citation: template.citation,
      isBusinessDays: template.isBusinessDays,
      includesHolidays: false,
      mcpSource: false
    };
  });
}