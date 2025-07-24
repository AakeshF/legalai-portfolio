import React, { useEffect, useState } from 'react';
import DatePicker from 'react-datepicker';
import { Calendar, AlertCircle, Info } from 'lucide-react';
import { isSameDay, getYear } from 'date-fns';
import { useCourtHolidays } from '../../services/mcp';
import { useSimpleMode } from '../../contexts/SimpleModeContext';
import { CourtHoliday } from './types';
import "react-datepicker/dist/react-datepicker.css";

interface DateInputWithCourtCalendarProps {
  label: string;
  value: Date | null;
  onChange: (date: Date | null) => void;
  jurisdiction?: string;
  minDate?: Date;
  maxDate?: Date;
  placeholder?: string;
  error?: string;
  required?: boolean;
}

export const DateInputWithCourtCalendar: React.FC<DateInputWithCourtCalendarProps> = ({
  label,
  value,
  onChange,
  jurisdiction,
  minDate,
  maxDate,
  placeholder = 'Select date',
  error,
  required = false
}) => {
  const { getSimpleText, isSimpleMode } = useSimpleMode();
  const [selectedYear, setSelectedYear] = useState(getYear(value || new Date()));
  
  // Fetch court holidays via MCP
  const { data: holidaysResponse, isLoading: loadingHolidays } = useCourtHolidays(
    selectedYear,
    jurisdiction || ''
  );
  
  const courtHolidays: CourtHoliday[] = holidaysResponse?.data || [];
  const holidayDates = courtHolidays.map(h => new Date(h.date));
  
  // Update year when date changes
  useEffect(() => {
    if (value) {
      const year = getYear(value);
      if (year !== selectedYear) {
        setSelectedYear(year);
      }
    }
  }, [value, selectedYear]);
  
  const isCourtHoliday = (date: Date): boolean => {
    return holidayDates.some(holiday => isSameDay(holiday, date));
  };
  
  const getHolidayName = (date: Date): string | undefined => {
    const holiday = courtHolidays.find(h => isSameDay(new Date(h.date), date));
    return holiday?.name;
  };
  
  const dayClassName = (date: Date): string => {
    if (isCourtHoliday(date)) {
      return 'court-holiday';
    }
    return '';
  };
  
  return (
    <div className="space-y-2">
      <label className={`block font-medium text-gray-700 ${
        isSimpleMode ? 'text-lg' : 'text-base'
      }`}>
        {getSimpleText(label)}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      
      <div className="relative">
        <div className="relative">
          <DatePicker
            selected={value}
            onChange={onChange}
            excludeDates={holidayDates}
            minDate={minDate}
            maxDate={maxDate}
            placeholderText={getSimpleText(placeholder)}
            className={`
              w-full pl-10 pr-3 rounded-lg border
              ${error ? 'border-red-500' : 'border-gray-300'}
              ${isSimpleMode ? 'py-3 text-lg' : 'py-2 text-base'}
              focus:outline-none focus:ring-2 focus:ring-blue-500
            `}
            dayClassName={dayClassName}
            showMonthDropdown
            showYearDropdown
            dropdownMode="select"
            dateFormat="MMM d, yyyy"
            onYearChange={setSelectedYear}
            renderDayContents={(dayOfMonth, date) => {
              const holidayName = date && getHolidayName(date);
              return (
                <div className="relative">
                  <span>{dayOfMonth}</span>
                  {holidayName && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="holiday-tooltip">
                        <span className="text-red-600 text-xs">•</span>
                        <div className="holiday-name">{holidayName}</div>
                      </div>
                    </div>
                  )}
                </div>
              );
            }}
          />
          <Calendar className={`absolute left-3 ${
            isSimpleMode ? 'top-3.5' : 'top-2.5'
          } w-5 h-5 text-gray-400 pointer-events-none`} />
        </div>
        
        {loadingHolidays && (
          <div className={`mt-1 text-blue-600 ${isSimpleMode ? 'text-base' : 'text-sm'}`}>
            {getSimpleText('Loading court holidays...')}
          </div>
        )}
        
        {jurisdiction && courtHolidays.length > 0 && (
          <div className={`mt-2 p-2 bg-blue-50 rounded-lg flex items-start ${
            isSimpleMode ? 'text-base' : 'text-sm'
          }`}>
            <Info className="w-4 h-4 text-blue-600 mr-2 flex-shrink-0 mt-0.5" />
            <span className="text-blue-800">
              {getSimpleText(`Court holidays excluded for ${jurisdiction}`)}
            </span>
          </div>
        )}
      </div>
      
      {error && (
        <p className={`text-red-600 flex items-center ${
          isSimpleMode ? 'text-base' : 'text-sm'
        }`}>
          <AlertCircle className="w-4 h-4 mr-1" />
          {getSimpleText(error)}
        </p>
      )}
      
      <style jsx>{`
        :global(.court-holiday) {
          background-color: #fee2e2 !important;
          color: #dc2626 !important;
          font-weight: 600;
        }
        
        :global(.court-holiday:hover) {
          background-color: #fecaca !important;
        }
        
        .holiday-tooltip {
          position: relative;
        }
        
        .holiday-name {
          display: none;
          position: absolute;
          bottom: 100%;
          left: 50%;
          transform: translateX(-50%);
          background: #1f2937;
          color: white;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          white-space: nowrap;
          z-index: 1000;
          margin-bottom: 4px;
        }
        
        .holiday-tooltip:hover .holiday-name {
          display: block;
        }
        
        :global(.react-datepicker) {
          font-family: inherit;
          border-radius: 0.5rem;
          border: 1px solid #e5e7eb;
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        
        :global(.react-datepicker__header) {
          background-color: #f9fafb;
          border-bottom: 1px solid #e5e7eb;
          padding-top: 0.5rem;
        }
        
        :global(.react-datepicker__day--selected) {
          background-color: #3b82f6;
        }
        
        :global(.react-datepicker__day--keyboard-selected) {
          background-color: #93c5fd;
        }
        
        ${isSimpleMode ? `
          :global(.react-datepicker) {
            font-size: 1.125rem;
          }
          
          :global(.react-datepicker__day) {
            width: 2.5rem;
            height: 2.5rem;
            line-height: 2.5rem;
          }
          
          :global(.react-datepicker__header) {
            padding: 1rem;
          }
          
          :global(.react-datepicker__current-month) {
            font-size: 1.25rem;
          }
        ` : ''}
      `}</style>
    </div>
  );
};