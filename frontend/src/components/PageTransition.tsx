import React, { useEffect, useState } from 'react';

interface PageTransitionProps {
  children: React.ReactNode;
  transitionKey: string;
}

export const PageTransition: React.FC<PageTransitionProps> = ({ children, transitionKey }) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(false);
    const timer = setTimeout(() => setIsVisible(true), 50);
    return () => clearTimeout(timer);
  }, [transitionKey]);

  return (
    <div 
      className={`transition-all duration-300 ${
        isVisible ? 'opacity-100 transform translate-y-0' : 'opacity-0 transform translate-y-4'
      }`}
    >
      {children}
    </div>
  );
};