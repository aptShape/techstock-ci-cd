import { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import { normalizeApiBase } from './api.js';

const API_URL = normalizeApiBase(import.meta.env.VITE_API_URL);

function App() {
  const [items, setItems] = useState([]);
  const [newItem, setNewItem] = useState({ name: '', price: 0, quantity: 0 });
  const [editingItem, setEditingItem] = useState(null);

  useEffect(() => {
    fetchItems();
  }, []);

  const fetchItems = async () => {
    try {
      const res = await axios.get(`${API_URL}/items`);
      setItems(res.data);
    } catch (error) {
      console.error('Error fetching items:', error);
    }
  };

  const addItem = async () => {
    try {
      await axios.post(`${API_URL}/items`, newItem);
      fetchItems();
      setNewItem({ name: '', price: 0, quantity: 0 });
    } catch (error) {
      console.error('Error adding item:', error);
    }
  };

  const updateItem = async (id) => {
    try {
      await axios.put(`${API_URL}/items/${id}`, editingItem);
      fetchItems();
      setEditingItem(null);
    } catch (error) {
      console.error('Error updating item:', error);
    }
  };

  const deleteItem = async (id) => {
    try {
      await axios.delete(`${API_URL}/items/${id}`);
      fetchItems();
    } catch (error) {
      console.error('Error deleting item:', error);
    }
  };

  const updateQuantity = async (id, action) => {
    try {
      await axios.put(`${API_URL}/items/${id}/quantity?action=${action}`);
      fetchItems();
    } catch (error) {
      console.error('Error updating quantity:', error);
    }
  };

  return (
    <div className="App">
      <h1>TechStock</h1>
      <p>IT Equipment Inventory Manager</p>
      <div>
        <h2>Add Equipment</h2>
        <input
          type="text"
          placeholder="Equipment name"
          value={newItem.name}
          onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
        />
        <input
          type="number"
          placeholder="Price"
          value={newItem.price}
          onChange={(e) => setNewItem({ ...newItem, price: parseFloat(e.target.value) })}
        />
        <input
          type="number"
          placeholder="Quantity"
          value={newItem.quantity}
          onChange={(e) => setNewItem({ ...newItem, quantity: parseInt(e.target.value) })}
        />
        <button onClick={addItem}>Add</button>
      </div>

      <h2>IT Equipment Inventory</h2>
      <ul>
        {items.map((item) => (
          <li key={item._id}>
            {editingItem && editingItem._id === item._id ? (
              <div>
                <input
                  type="text"
                  value={editingItem.name}
                  onChange={(e) => setEditingItem({ ...editingItem, name: e.target.value })}
                />
                <input
                  type="number"
                  value={editingItem.price}
                  onChange={(e) => setEditingItem({ ...editingItem, price: parseFloat(e.target.value) })}
                />
                <input
                  type="number"
                  value={editingItem.quantity}
                  onChange={(e) => setEditingItem({ ...editingItem, quantity: parseInt(e.target.value) })}
                />
                <button onClick={() => updateItem(item._id)}>Update</button>
                <button onClick={() => setEditingItem(null)}>Cancel</button>
              </div>
            ) : (
              <div>
                {item.name} - ${item.price} - Quantity: {item.quantity}
                <button onClick={() => updateQuantity(item._id, 'add')}>+1</button>
                <button onClick={() => updateQuantity(item._id, 'remove')}>-1</button>
                <button onClick={() => setEditingItem(item)}>Edit</button>
                <button onClick={() => deleteItem(item._id)}>Delete</button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;
