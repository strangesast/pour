var mongoose = require('mongoose');
var Schema = mongoose.Schema;

var Kegerator = new Schema({
  name: {
    type: String,
    index: {
      unique: true
    }
  },
  location: String,
  address: String,
  port: Number
}, {
  timestamps: true
});

Kegerator.index({address: 1, port: 1}, {unique: true});

module.exports = mongoose.model('Kegerator', Kegerator);
