import React, { useState } from 'react';
import { 
  ChevronDown, 
  ChevronUp, 
  Copy, 
  Check,
  FileText,
  Calendar,
  DollarSign,
  Scale,
  AlertTriangle,
  Users,
  Building,
  User,
  MapPin,
  Hash,
  Shield,
  Clock,
  Briefcase
} from 'lucide-react';
import { useToast } from './Toast';

interface MetadataSectionProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultExpanded?: boolean;
  badge?: React.ReactNode;
}

export const MetadataSection: React.FC<MetadataSectionProps> = ({ 
  title, 
  icon, 
  children, 
  defaultExpanded = true,
  badge 
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center space-x-3">
          <div className="text-slate-700">{icon}</div>
          <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
          {badge && <div>{badge}</div>}
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-slate-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-slate-400" />
        )}
      </button>
      
      {isExpanded && (
        <div className="px-6 pb-6 border-t border-slate-100">
          {children}
        </div>
      )}
    </div>
  );
};

interface MetadataFieldProps {
  label: string;
  value: string | number | undefined;
  icon?: React.ReactNode;
  copyable?: boolean;
  className?: string;
  valueClassName?: string;
}

export const MetadataField: React.FC<MetadataFieldProps> = ({ 
  label, 
  value, 
  icon,
  copyable = false,
  className = '',
  valueClassName = ''
}) => {
  const [copied, setCopied] = useState(false);
  const { showSuccess } = useToast();

  const handleCopy = async () => {
    if (!value) return;
    
    try {
      await navigator.clipboard.writeText(value.toString());
      setCopied(true);
      showSuccess('Copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  if (!value) return null;

  return (
    <div className={`flex items-start space-x-3 py-2 ${className}`}>
      {icon && <div className="text-slate-500 mt-0.5">{icon}</div>}
      <div className="flex-1">
        <p className="text-sm text-slate-600">{label}</p>
        <div className="flex items-center space-x-2">
          <p className={`font-medium text-slate-900 ${valueClassName}`}>{value}</p>
          {copyable && (
            <button
              onClick={handleCopy}
              className="p-1 hover:bg-slate-100 rounded transition-colors"
              title="Copy to clipboard"
            >
              {copied ? (
                <Check className="w-4 h-4 text-green-600" />
              ) : (
                <Copy className="w-4 h-4 text-slate-400" />
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

interface RiskBadgeProps {
  severity: 'low' | 'medium' | 'high';
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ severity, className = '' }) => {
  const getStyles = () => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'low':
        return 'bg-green-100 text-green-700 border-green-200';
    }
  };

  const getIcon = () => {
    switch (severity) {
      case 'high':
        return <AlertTriangle className="w-4 h-4" />;
      case 'medium':
        return <AlertTriangle className="w-4 h-4" />;
      case 'low':
        return <Shield className="w-4 h-4" />;
    }
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${getStyles()} ${className}`}>
      {getIcon()}
      <span className="ml-1">{severity.toUpperCase()} RISK</span>
    </span>
  );
};

interface PartyCardProps {
  party: {
    name: string;
    role: string;
    type?: 'individual' | 'organization';
    contact?: {
      email?: string;
      phone?: string;
      address?: string;
    };
  };
}

export const PartyCard: React.FC<PartyCardProps> = ({ party }) => {
  return (
    <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
      <div className="flex items-start space-x-3">
        <div className="p-2 bg-white rounded-lg">
          {party.type === 'organization' ? 
            <Building className="w-5 h-5 text-slate-600" /> : 
            <User className="w-5 h-5 text-slate-600" />
          }
        </div>
        <div className="flex-1">
          <h4 className="font-semibold text-slate-900">{party.name}</h4>
          <p className="text-sm text-slate-600 mt-0.5">{party.role}</p>
          
          {party.contact && (
            <div className="mt-3 space-y-1">
              {party.contact.email && (
                <MetadataField
                  label="Email"
                  value={party.contact.email}
                  copyable
                  className="py-1"
                />
              )}
              {party.contact.phone && (
                <MetadataField
                  label="Phone"
                  value={party.contact.phone}
                  copyable
                  className="py-1"
                />
              )}
              {party.contact.address && (
                <MetadataField
                  label="Address"
                  value={party.contact.address}
                  className="py-1"
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

interface DateTimelineProps {
  dates: Array<{
    date: string;
    type: string;
    description?: string;
  }>;
}

export const DateTimeline: React.FC<DateTimelineProps> = ({ dates }) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const sortedDates = [...dates].sort((a, b) => 
    new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  return (
    <div className="relative">
      <div className="absolute left-6 top-8 bottom-0 w-0.5 bg-slate-200"></div>
      <div className="space-y-4">
        {sortedDates.map((event, index) => (
          <div key={index} className="flex items-start space-x-4">
            <div className="relative z-10 p-2 bg-blue-100 rounded-full">
              <Calendar className="w-4 h-4 text-blue-600" />
            </div>
            <div className="flex-1 pb-4">
              <div className="bg-white rounded-lg p-4 border border-slate-200">
                <div className="flex items-baseline justify-between mb-1">
                  <h4 className="font-semibold text-slate-900">{event.type}</h4>
                  <time className="text-sm text-slate-600">{formatDate(event.date)}</time>
                </div>
                {event.description && (
                  <p className="text-sm text-slate-700 mt-1">{event.description}</p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

interface FinancialAmountProps {
  amount: {
    amount: number;
    currency: string;
    context: string;
    payment_schedule?: string;
  };
}

export const FinancialAmount: React.FC<FinancialAmountProps> = ({ amount }) => {
  const formatCurrency = (value: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(value);
  };

  return (
    <div className="p-4 bg-green-50 rounded-lg border border-green-200">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-2xl font-bold text-green-900 mb-1">
            {formatCurrency(amount.amount, amount.currency)}
          </div>
          <p className="text-sm text-green-700">{amount.context}</p>
          {amount.payment_schedule && (
            <p className="text-xs text-green-600 mt-2">
              <Clock className="w-3 h-3 inline mr-1" />
              {amount.payment_schedule}
            </p>
          )}
        </div>
        <DollarSign className="w-6 h-6 text-green-600" />
      </div>
    </div>
  );
};

export default MetadataSection;