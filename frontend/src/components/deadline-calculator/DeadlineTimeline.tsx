import React from 'react';
import { Calendar, AlertCircle, Clock, Gavel, FileText, ChevronRight } from 'lucide-react';
import { format, differenceInDays } from 'date-fns';
import { Deadline } from './types';
import { useSimpleMode } from '../../contexts/SimpleModeContext';
import { getDeadlineSeverity, groupDeadlinesByMonth } from './utils';

interface DeadlineTimelineProps {
  deadlines: Deadline[];
  onDeadlineClick?: (deadline: Deadline) => void;
}

export const DeadlineTimeline: React.FC<DeadlineTimelineProps> = ({ 
  deadlines, 
  onDeadlineClick 
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const groupedDeadlines = groupDeadlinesByMonth(deadlines);
  
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'red';
      case 'high': return 'orange';
      case 'medium': return 'yellow';
      case 'low': return 'green';
      default: return 'gray';
    }
  };
  
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'statute_of_limitations': return AlertCircle;
      case 'filing': return FileText;
      case 'hearing': return Gavel;
      default: return Calendar;
    }
  };
  
  return (
    <div className="space-y-8">
      {Object.entries(groupedDeadlines).map(([month, monthDeadlines]) => (
        <div key={month}>
          <h3 className={`font-semibold text-gray-900 mb-4 ${
            isSimpleMode ? 'text-xl' : 'text-lg'
          }`}>
            {month}
          </h3>
          
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200" />
            
            {/* Timeline items */}
            <div className="space-y-4">
              {monthDeadlines.map((deadline, index) => {
                const severity = getDeadlineSeverity(deadline);
                const color = getSeverityColor(severity);
                const Icon = getTypeIcon(deadline.type);
                const daysUntil = differenceInDays(deadline.date, new Date());
                
                return (
                  <div
                    key={deadline.id}
                    className={`relative flex items-start ${
                      onDeadlineClick ? 'cursor-pointer group' : ''
                    }`}
                    onClick={() => onDeadlineClick?.(deadline)}
                  >
                    {/* Timeline dot */}
                    <div className={`
                      absolute left-4 w-4 h-4 rounded-full border-4 border-white z-10
                      ${severity === 'critical' ? 'bg-red-500 animate-pulse' : ''}
                      ${severity === 'high' ? 'bg-orange-500' : ''}
                      ${severity === 'medium' ? 'bg-yellow-500' : ''}
                      ${severity === 'low' ? 'bg-green-500' : ''}
                    `} />
                    
                    {/* Content */}
                    <div className={`
                      ml-12 flex-1 p-4 rounded-lg border-2 transition-all
                      ${onDeadlineClick ? 'group-hover:shadow-md group-hover:border-blue-300' : ''}
                      ${severity === 'critical' ? 'bg-red-50 border-red-200' : ''}
                      ${severity === 'high' ? 'bg-orange-50 border-orange-200' : ''}
                      ${severity === 'medium' ? 'bg-yellow-50 border-yellow-200' : ''}
                      ${severity === 'low' ? 'bg-green-50 border-green-200' : ''}
                    `}>
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-3">
                          <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0
                            ${severity === 'critical' ? 'text-red-600' : ''}
                            ${severity === 'high' ? 'text-orange-600' : ''}
                            ${severity === 'medium' ? 'text-yellow-600' : ''}
                            ${severity === 'low' ? 'text-green-600' : ''}
                          `} />
                          
                          <div className="flex-1">
                            <h4 className={`font-semibold ${
                              severity === 'critical' ? 'text-red-900' : ''
                            } ${severity === 'high' ? 'text-orange-900' : ''
                            } ${severity === 'medium' ? 'text-yellow-900' : ''
                            } ${severity === 'low' ? 'text-green-900' : ''
                            } ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
                              {getSimpleText(deadline.title)}
                            </h4>
                            
                            {deadline.description && (
                              <p className={`mt-1 ${
                                severity === 'critical' ? 'text-red-700' : ''
                              } ${severity === 'high' ? 'text-orange-700' : ''
                              } ${severity === 'medium' ? 'text-yellow-700' : ''
                              } ${severity === 'low' ? 'text-green-700' : ''
                              } ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
                                {getSimpleText(deadline.description)}
                              </p>
                            )}
                            
                            <div className={`mt-2 flex flex-wrap items-center gap-4 ${
                              isSimpleMode ? 'text-sm' : 'text-xs'
                            }`}>
                              <span className={`flex items-center
                                ${severity === 'critical' ? 'text-red-600' : ''}
                                ${severity === 'high' ? 'text-orange-600' : ''}
                                ${severity === 'medium' ? 'text-yellow-600' : ''}
                                ${severity === 'low' ? 'text-green-600' : ''}
                              `}>
                                <Calendar className="w-3 h-3 mr-1" />
                                {format(deadline.date, 'MMM d, yyyy')}
                              </span>
                              
                              <span className={`flex items-center
                                ${severity === 'critical' ? 'text-red-600' : ''}
                                ${severity === 'high' ? 'text-orange-600' : ''}
                                ${severity === 'medium' ? 'text-yellow-600' : ''}
                                ${severity === 'low' ? 'text-green-600' : ''}
                              `}>
                                <Clock className="w-3 h-3 mr-1" />
                                {daysUntil > 0 
                                  ? getSimpleText(`${daysUntil} days remaining`)
                                  : daysUntil === 0 
                                    ? getSimpleText('Due today')
                                    : getSimpleText(`${Math.abs(daysUntil)} days overdue`)
                                }
                              </span>
                              
                              {deadline.citation && (
                                <span className="text-gray-500">
                                  {deadline.citation}
                                </span>
                              )}
                              
                              {deadline.mcpSource && (
                                <span className="text-blue-600 flex items-center">
                                  <Wifi className="w-3 h-3 mr-1" />
                                  {getSimpleText('Court verified')}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        
                        {onDeadlineClick && (
                          <ChevronRight className={`
                            w-5 h-5 text-gray-400 group-hover:text-blue-600 
                            transition-colors flex-shrink-0
                          `} />
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ))}
      
      {deadlines.length === 0 && (
        <div className="text-center py-12">
          <Calendar className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className={`text-gray-500 ${isSimpleMode ? 'text-lg' : 'text-base'}`}>
            {getSimpleText('No deadlines calculated yet')}
          </p>
        </div>
      )}
    </div>
  );
};

// Import required icons
import { Wifi } from 'lucide-react';