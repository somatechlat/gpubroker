
import React from 'react';
import { createComponent } from '@lit/react';
import { EogButton as EogButtonElement } from './EogButton';
import { EogHeader as EogHeaderElement } from './EogHeader';
import { EogKpiCard as EogKpiCardElement } from './EogKpiCard';
import { EogProviderCard as EogProviderCardElement } from './EogProviderCard';

export const EogButton = createComponent({
    tagName: 'eog-button',
    elementClass: EogButtonElement,
    react: React,
    events: {
        onClick: 'click',
    },
});

export const EogHeader = createComponent({
    tagName: 'eog-header',
    elementClass: EogHeaderElement,
    react: React,
});

export const EogKpiCard = createComponent({
    tagName: 'eog-kpi-card',
    elementClass: EogKpiCardElement,
    react: React,
});

export const EogProviderCard = createComponent({
    tagName: 'eog-provider-card',
    elementClass: EogProviderCardElement,
    react: React,
    events: {
        onBook: 'book',
    },
});
