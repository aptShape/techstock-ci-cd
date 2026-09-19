import assert from 'node:assert/strict';
import test from 'node:test';
import { normalizeApiBase } from '../src/api.js';

for (const [input, expected] of [
  [undefined, '/api'],
  ['', '/api'],
  ['/', '/api'],
  ['/api', '/api'],
  ['/api/', '/api'],
  ['/api/api/', '/api'],
  ['http://techstock.local', 'http://techstock.local/api'],
  ['http://localhost:8000/', 'http://localhost:8000/api'],
  ['http://localhost:8000/api/', 'http://localhost:8000/api'],
  [' https://techstock.local/api ', 'https://techstock.local/api'],
]) {
  test(`API base ${JSON.stringify(input)} produces a single /api prefix`, () => {
    assert.equal(`${normalizeApiBase(input)}/items`, `${expected}/items`);
  });
}
