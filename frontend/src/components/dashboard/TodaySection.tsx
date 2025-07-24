import React from 'react';
import { 
  Calendar, Clock, MapPin, Gavel, Video, 
  AlertCircle, CheckCircle, User, FileText 
} from 'lucide-react';
import { format, isToday, isSameDay } from 'date-fns';
import { CourtAppearance, DeadlineAlert, FollowUpReminder } from './types';
import { useSimpleMode } from '../../contexts/SimpleModeContext';
import { SimpleModeCard } from '../SimpleModeWrapper';

interface AppearanceCardProps {
  appearance: CourtAppearance;
  isFromMCP?: boolean;
}

const AppearanceCard: React.FC<AppearanceCardProps> = ({ appearance, isFromMCP = false }) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  return (
    <div className="p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          {appearance.isVirtual ? (
            <Video className="w-5 h-5 text-blue-600 mt-0.5" />
          ) : (
            <Gavel className="w-5 h-5 text-gray-600 mt-0.5" />
          )}
          
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h4 className={`font-semibold text-gray-900 ${
                isSimpleMode ? 'text-lg' : 'text-base'
              }`}>
                {appearance.time}
              </h4>
              {isFromMCP && (
                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                  {getSimpleText('Live Data')}
                </span>
              )}
            </div>
            
            <p className={`text-gray-700 mt-1 ${
              isSimpleMode ? 'text-base' : 'text-sm'
            }`}>
              {appearance.caseName}
            </p>
            
            <div className={`mt-2 space-y-1 ${
              isSimpleMode ? 'text-sm' : 'text-xs'
            } text-gray-600`}>
              <div className="flex items-center space-x-2">
                <MapPin className="w-3 h-3" />
                <span>
                  {appearance.isVirtual 
                    ? getSimpleText('Virtual Hearing') 
                    : appearance.courtroom
                  }
                </span>
              </div>
              
              <div className="flex items-center space-x-2">
                <User className="w-3 h-3" />
                <span>{getSimpleText(`Judge ${appearance.judge}`)}</span>
              </div>
              
              {appearance.caseNumber && (
                <div className="flex items-center space-x-2">
                  <FileText className="w-3 h-3" />
                  <span>{appearance.caseNumber}</span>
                </div>
              )}
            </div>
            
            {appearance.isVirtual && appearance.virtualLink && (
              <a
                href={appearance.virtualLink}
                target="_blank"
                rel="noopener noreferrer"
                className={`
                  inline-flex items-center mt-3 px-3 py-1.5 
                  bg-blue-600 text-white rounded-lg hover:bg-blue-700
                  transition-colors font-medium
                  ${isSimpleMode ? 'text-base' : 'text-sm'}
                `}
              >
                {getSimpleText('Join Virtual Hearing')}
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

interface DeadlineAlertItemProps {
  deadline: DeadlineAlert;
}

const DeadlineAlertItem: React.FC<DeadlineAlertItemProps> = ({ deadline }) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'urgent': return 'red';
      case 'high': return 'orange';
      case 'medium': return 'yellow';
      default: return 'gray';
    }
  };
  
  const color = getSeverityColor(deadline.severity);
  
  return (
    <div className={`
      p-3 rounded-lg border-l-4
      ${color === 'red' ? 'bg-red-50 border-red-500' : ''}
      ${color === 'orange' ? 'bg-orange-50 border-orange-500' : ''}
      ${color === 'yellow' ? 'bg-yellow-50 border-yellow-500' : ''}
      ${color === 'gray' ? 'bg-gray-50 border-gray-500' : ''}
    `}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h5 className={`font-medium ${
            color === 'red' ? 'text-red-900' : ''
          } ${color === 'orange' ? 'text-orange-900' : ''
          } ${color === 'yellow' ? 'text-yellow-900' : ''
          } ${color === 'gray' ? 'text-gray-900' : ''
          } ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
            {getSimpleText(deadline.title)}
          </h5>
          
          <p className={`mt-1 ${
            color === 'red' ? 'text-red-700' : ''
          } ${color === 'orange' ? 'text-orange-700' : ''
          } ${color === 'yellow' ? 'text-yellow-700' : ''
          } ${color === 'gray' ? 'text-gray-700' : ''
          } ${isSimpleMode ? 'text-sm' : 'text-xs'}`}>
            {deadline.matterName}
          </p>
        </div>
        
        <span className={`
          px-2 py-1 rounded-full text-xs font-medium
          ${color === 'red' ? 'bg-red-200 text-red-800' : ''}
          ${color === 'orange' ? 'bg-orange-200 text-orange-800' : ''}
          ${color === 'yellow' ? 'bg-yellow-200 text-yellow-800' : ''}
          ${color === 'gray' ? 'bg-gray-200 text-gray-800' : ''}
        `}>
          {deadline.daysRemaining === 0 
            ? getSimpleText('Today')
            : deadline.daysRemaining === 1
              ? getSimpleText('Tomorrow')
              : getSimpleText(`${deadline.daysRemaining} days`)
          }
        </span>
      </div>
    </div>
  );
};

interface TodaySectionProps {
  courtData?: CourtAppearance[];
  deadlines?: DeadlineAlert[];
  followUps?: FollowUpReminder[];
}

export const TodaySection: React.FC<TodaySectionProps> = ({ 
  courtData = [], 
  deadlines = [],
  followUps = []
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const today = new Date();
  
  // Filter today's appearances
  const todayAppearances = courtData.filter(app => 
    isToday(new Date(app.date))
  );
  
  // Filter urgent deadlines (today or tomorrow)
  const urgentDeadlines = deadlines.filter(d => 
    d.daysRemaining <= 1 || d.severity === 'urgent'
  );
  
  // Filter today's follow-ups
  const todayFollowUps = followUps.filter(f => 
    isSameDay(new Date(f.dueDate), today)
  );
  
  return (
    <SimpleModeCard className="today-section">
      <div className="mb-6">
        <h2 className={`font-bold text-gray-900 flex items-center ${
          isSimpleMode ? 'text-2xl' : 'text-xl'
        }`}>
          <Calendar className="w-6 h-6 mr-3" />
          {getSimpleText(`Today - ${format(today, 'EEEE, MMMM d')}`)}
        </h2>
      </div>
      
      {/* Court Appearances */}
      {todayAppearances.length > 0 && (
        <div className="mb-6">
          <h3 className={`font-semibold text-gray-800 mb-3 flex items-center ${
            isSimpleMode ? 'text-lg' : 'text-base'
          }`}>
            <Gavel className="w-5 h-5 mr-2" />
            {getSimpleText('Court Appearances')}
            <span className="ml-2 px-2 py-0.5 bg-gray-100 text-gray-700 text-sm rounded-full">
              {todayAppearances.length}
            </span>
          </h3>
          
          <div className="space-y-3">
            {todayAppearances.map(appearance => (
              <AppearanceCard 
                key={appearance.id}
                appearance={appearance}
                isFromMCP={true}
              />
            ))}
          </div>
        </div>
      )}
      
      {/* Deadline Alerts */}
      {urgentDeadlines.length > 0 && (
        <div className="mb-6">
          <h3 className={`font-semibold text-gray-800 mb-3 flex items-center ${
            isSimpleMode ? 'text-lg' : 'text-base'
          }`}>
            <AlertCircle className="w-5 h-5 mr-2 text-red-600" />
            {getSimpleText('Urgent Deadlines')}
            <span className="ml-2 px-2 py-0.5 bg-red-100 text-red-700 text-sm rounded-full">
              {urgentDeadlines.length}
            </span>
          </h3>
          
          <div className="space-y-2">
            {urgentDeadlines.map(deadline => (
              <DeadlineAlertItem 
                key={deadline.id}
                deadline={deadline}
              />
            ))}
          </div>
        </div>
      )}
      
      {/* Follow-up Reminders */}
      {todayFollowUps.length > 0 && (
        <div>
          <h3 className={`font-semibold text-gray-800 mb-3 flex items-center ${
            isSimpleMode ? 'text-lg' : 'text-base'
          }`}>
            <CheckCircle className="w-5 h-5 mr-2 text-green-600" />
            {getSimpleText('Follow-ups Due')}
            <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-700 text-sm rounded-full">
              {todayFollowUps.length}
            </span>
          </h3>
          
          <div className="space-y-2">
            {todayFollowUps.map(followUp => (
              <div 
                key={followUp.id}
                className="p-3 bg-gray-50 rounded-lg flex items-start space-x-3"
              >
                <CheckCircle className="w-4 h-4 text-gray-400 mt-0.5" />
                <div className="flex-1">
                  <p className={`text-gray-900 ${
                    isSimpleMode ? 'text-base' : 'text-sm'
                  }`}>
                    {getSimpleText(`${followUp.type === 'call' ? 'Call' : 
                      followUp.type === 'email' ? 'Email' : 
                      followUp.type === 'meeting' ? 'Meet with' : 
                      'Send document to'} ${followUp.clientName}`)}
                  </p>
                  <p className={`text-gray-600 mt-1 ${
                    isSimpleMode ? 'text-sm' : 'text-xs'
                  }`}>
                    {followUp.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Empty State */}
      {todayAppearances.length === 0 && 
       urgentDeadlines.length === 0 && 
       todayFollowUps.length === 0 && (
        <div className="text-center py-8">
          <Calendar className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className={`text-gray-500 ${
            isSimpleMode ? 'text-lg' : 'text-base'
          }`}>
            {getSimpleText('No urgent items for today')}
          </p>
        </div>
      )}
    </SimpleModeCard>
  );
};