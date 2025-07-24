import React, { useEffect, useState } from 'react';
import { CheckCircle, Sparkles } from 'lucide-react';

interface SuccessCelebrationProps {
  show: boolean;
  message?: string;
  onComplete?: () => void;
}

export const SuccessCelebration: React.FC<SuccessCelebrationProps> = ({ 
  show, 
  message = 'Success!',
  onComplete 
}) => {
  const [particles, setParticles] = useState<Array<{ id: number; color: string; delay: number; x: number }>>([]);

  useEffect(() => {
    if (show) {
      // Generate confetti particles
      const newParticles = Array.from({ length: 20 }, (_, i) => ({
        id: i,
        color: ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444'][Math.floor(Math.random() * 5)],
        delay: Math.random() * 0.5,
        x: Math.random() * window.innerWidth
      }));
      setParticles(newParticles);

      // Clear particles after animation
      const timer = setTimeout(() => {
        setParticles([]);
        if (onComplete) onComplete();
      }, 3000);

      return () => clearTimeout(timer);
    }
  }, [show, onComplete]);

  if (!show) return null;

  return (
    <>
      {/* Confetti particles */}
      {particles.map(particle => (
        <div
          key={particle.id}
          className="confetti"
          style={{
            backgroundColor: particle.color,
            left: `${particle.x}px`,
            animationDelay: `${particle.delay}s`,
            borderRadius: Math.random() > 0.5 ? '50%' : '0'
          }}
        />
      ))}

      {/* Success message */}
      <div className="fixed inset-0 pointer-events-none flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl shadow-2xl p-8 animate-success pointer-events-auto">
          <div className="flex flex-col items-center text-center">
            <div className="relative mb-4">
              <div className="absolute inset-0 bg-green-500 rounded-full animate-ping"></div>
              <div className="relative p-4 bg-green-100 rounded-full">
                <CheckCircle className="w-12 h-12 text-green-600" />
              </div>
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-2">{message}</h3>
            <div className="flex items-center space-x-1 text-green-600">
              <Sparkles className="w-4 h-4" />
              <span className="text-sm font-medium">Processing Complete</span>
              <Sparkles className="w-4 h-4" />
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

interface MiniSuccessProps {
  show: boolean;
  x: number;
  y: number;
}

export const MiniSuccess: React.FC<MiniSuccessProps> = ({ show, x, y }) => {
  if (!show) return null;

  return (
    <div 
      className="fixed pointer-events-none z-50 animate-success"
      style={{ left: x, top: y }}
    >
      <div className="relative">
        <div className="absolute inset-0 bg-green-500 rounded-full animate-ping"></div>
        <CheckCircle className="w-8 h-8 text-green-500 relative" />
      </div>
    </div>
  );
};