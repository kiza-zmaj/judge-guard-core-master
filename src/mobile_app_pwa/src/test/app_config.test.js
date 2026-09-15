import { describe, it, expect } from 'vitest';
import appConfig from '../../public/app_config.json';

describe('app_config.json', () => {
  it('contains a title field', () => {
    expect(appConfig).toHaveProperty('title');
    expect(typeof appConfig.title).toBe('string');
  });

  it('contains a theme field', () => {
    expect(appConfig).toHaveProperty('theme');
    expect(typeof appConfig.theme).toBe('string');
  });

  it('contains a content field', () => {
    expect(appConfig).toHaveProperty('content');
    expect(typeof appConfig.content).toBe('string');
  });

  it('contains a components array', () => {
    expect(appConfig).toHaveProperty('components');
    expect(Array.isArray(appConfig.components)).toBe(true);
  });

  it('validates last_verdict schema if present', () => {
    if (appConfig.last_verdict) {
      expect(appConfig.last_verdict).toHaveProperty('action');
      expect(appConfig.last_verdict).toHaveProperty('status');
      expect(appConfig.last_verdict).toHaveProperty('reason');
      expect(appConfig.last_verdict).toHaveProperty('timestamp');
    }
  });

  it('has components as an empty array by default', () => {
    expect(appConfig.components).toHaveLength(0);
  });

  it('has the correct title value', () => {
    expect(appConfig.title).toBe('Antigravity Mobile');
  });

  it('has required top-level keys (title, theme, content, components)', () => {
    const keys = Object.keys(appConfig);
    expect(keys).toEqual(expect.arrayContaining(['title', 'theme', 'content', 'components']));
    expect(keys.length).toBeGreaterThanOrEqual(4);
  });
});