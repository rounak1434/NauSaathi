import type { OriginOption, DestinationPort } from '../types';

export const ORIGIN_OPTIONS: OriginOption[] = [
  {
    country: 'Australia',
    ports: [
      { name: 'Port Hedland', country: 'Australia' },
      { name: 'Newcastle', country: 'Australia' },
      { name: 'Hay Point', country: 'Australia' },
    ],
  },
  {
    country: 'United States',
    ports: [
      { name: 'Hampton Roads', country: 'United States' },
    ],
  },
  {
    country: 'Mozambique',
    ports: [
      { name: 'Maputo', country: 'Mozambique' },
    ],
  },
  {
    country: 'Indonesia',
    ports: [
      { name: 'Balikpapan', country: 'Indonesia' },
      { name: 'Muara Berau', country: 'Indonesia' },
    ],
  },
  {
    country: 'Russia',
    ports: [
      { name: 'Vostochny', country: 'Russia' },
    ],
  },
];

export const DESTINATION_PORTS: DestinationPort[] = [
  { name: 'Paradip', state: 'Odisha' },
  { name: 'Visakhapatnam', state: 'Andhra Pradesh' },
  { name: 'Gangavaram', state: 'Andhra Pradesh' },
  { name: 'Gopalpur', state: 'Odisha' },
  { name: 'Dhamra', state: 'Odisha' },
  { name: 'Sagar-Sandheads', state: 'West Bengal' },
  { name: 'Haldia', state: 'West Bengal' },
];

export const CHARTERING_WINDOW_LABELS: Record<string, string> = {
  within_7_days: 'Within 7 Days',
  within_30_days: 'Within 30 Days',
  within_60_days: 'Within 60 Days',
  within_90_days: 'Within 90 Days',
  custom: 'Custom Date / Range',
};
