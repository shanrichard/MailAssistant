/**
 * Basic Test - No imports required
 * 基础测试 - 不需要导入
 */

export {}; // Make this a module

test('Basic math test', () => {
  expect(1 + 1).toBe(2);
});

test('String test', () => {
  expect('hello').toBe('hello');
});

test('Array test', () => {
  const arr = [1, 2, 3];
  expect(arr).toHaveLength(3);
});