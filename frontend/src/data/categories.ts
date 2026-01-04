import type { Category } from '../types';

export const categories: Category[] = [
  {
    key: 'musical-instruments',
    label: 'Musical Instruments',
    description: 'Guitars, keys, drums, and more.',
    filterConfigs: [
      {
        key: 'reverb-acoustic-guitars',
        label: 'Reverb Acoustic Guitars',
        description: 'Acoustic guitars curated from Reverb.'
      },
      {
        key: 'reverb-cymbals',
        label: 'Reverb Cymbals',
        description: 'Crash, ride, and hi-hat finds.'
      }
    ]
  },
  {
    key: 'clothing',
    label: 'Clothing',
    description: 'Essentials, outerwear, and statement pieces.',
    filterConfigs: [
      {
        key: 'vintage-denim',
        label: 'Vintage Denim',
        description: 'Curated denim drops and washes.'
      },
      {
        key: 'technical-outerwear',
        label: 'Technical Outerwear',
        description: 'Weather-ready layers and shells.'
      }
    ]
  },
  {
    key: 'vehicles',
    label: 'Vehicles',
    description: 'Cars, bikes, and mobility options.',
    filterConfigs: [
      {
        key: 'electric-sedans',
        label: 'Electric Sedans',
        description: 'Range-forward daily drivers.'
      },
      {
        key: 'adventure-suvs',
        label: 'Adventure SUVs',
        description: 'Roomy SUVs ready for road trips.'
      }
    ]
  },
  {
    key: 'wearable-accessories',
    label: 'Wearable Accessories',
    description: 'Watches, bags, and daily carry.',
    filterConfigs: [
      {
        key: 'luxury-watches',
        label: 'Luxury Watches',
        description: 'Heritage timepieces and icons.'
      },
      {
        key: 'everyday-bags',
        label: 'Everyday Bags',
        description: 'Totes, packs, and commuters.'
      }
    ]
  },
  {
    key: 'entertainment',
    label: 'Entertainment',
    description: 'Tickets, events, and experiences.',
    filterConfigs: [
      {
        key: 'concert-tickets',
        label: 'Concert Tickets',
        description: 'Live music and tours.'
      },
      {
        key: 'festival-passes',
        label: 'Festival Passes',
        description: 'Multi-day lineups and perks.'
      }
    ]
  },
  {
    key: 'flights',
    label: 'Flights',
    description: 'Compare routes and fares.',
    filterConfigs: [
      {
        key: 'weekend-getaways',
        label: 'Weekend Getaways',
        description: 'Quick trips with flexible timing.'
      },
      {
        key: 'red-eye-deals',
        label: 'Red-Eye Deals',
        description: 'Overnight flights with savings.'
      }
    ]
  }
];
