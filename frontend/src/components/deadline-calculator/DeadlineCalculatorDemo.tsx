import React from 'react';
import { DeadlineCalculator } from './DeadlineCalculator';
import { Deadline } from './types';
import { SimpleModeWrapper } from '../SimpleModeWrapper';

export const DeadlineCalculatorDemo: React.FC = () => {
  const handleDeadlinesCalculated = (deadlines: Deadline[]) => {
    console.log('Deadlines calculated:', deadlines);
  };
  
  return (
    <SimpleModeWrapper className="min-h-screen bg-gray-50">
      <div className="py-8">
        <DeadlineCalculator 
          matterId="DEMO-2024-001"
          onDeadlinesCalculated={handleDeadlinesCalculated}
        />
      </div>
    </SimpleModeWrapper>
  );
};

export default DeadlineCalculatorDemo;